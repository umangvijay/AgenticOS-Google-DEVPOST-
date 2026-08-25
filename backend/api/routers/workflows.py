"""
AgentOS — Workflows Router

POST /api/v1/workflows              — Create workflow from goal
GET  /api/v1/workflows              — List user's workflows
GET  /api/v1/workflows/{id}         — Get workflow detail
GET  /api/v1/workflows/{id}/events  — SSE event stream
POST /api/v1/workflows/{id}/cancel  — Cancel a running workflow
POST /api/v1/workflows/{id}/retry   — Retry a failed workflow
"""

import uuid
import json
import asyncio
import logging
import traceback

from fastapi import APIRouter, HTTPException, Request, Depends, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.api.dependencies.auth import get_current_user, AuthenticatedUser, require_not_viewer
from backend.security.input_sanitizer import sanitize_goal, InputValidationError
from backend.security.rate_limiter import check_rate_limit
from backend.security.rbac import require_resource_owner
from backend.config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workflows", tags=["workflows"])


def _get_factory(request: Request):
    factory = getattr(request.app.state, "factory", None)
    if not factory:
        raise HTTPException(status_code=500, detail="Server not initialized")
    return factory


class GoalRequest(BaseModel):
    goal: str


# ══════════════════════════════════════════════════════════════════
#  CREATE WORKFLOW
# ══════════════════════════════════════════════════════════════════

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_workflow(
    body: GoalRequest,
    request: Request,
    user: AuthenticatedUser = Depends(require_not_viewer),
):
    """
    Process a user's goal through intent → plan → execute.
    Real-time AI processing — no hardcoded responses.
    """
    factory = _get_factory(request)
    workflow_engine = getattr(request.app.state, "workflow_engine", None)
    if not workflow_engine:
        raise HTTPException(status_code=500, detail="Workflow engine not initialized")

    check_rate_limit(f"user:{user.user_id}", "workflow")

    try:
        goal = sanitize_goal(body.goal)
    except InputValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)

    if not goal:
        raise HTTPException(status_code=400, detail="Goal cannot be empty")

    run_id = str(uuid.uuid4())
    workflow_id = f"wf-{run_id[:8]}"

    try:
        from backend.models.schemas import (
            WorkflowRun, Task, TaskStatus, WorkflowDefinition,
            WorkflowEvent, WorkflowEventType,
        )
        from backend.agents.intent.intent_agent import get_intent_agent
        from backend.agents.planner.planner_agent import get_planner_agent
        from backend.engine.dag_validator import validate_dag, DAGValidationError
        from google.adk.runners import InMemoryRunner

        def extract_event_text(events):
            for event in reversed(events):
                if event.output is not None:
                    if hasattr(event.output, 'model_dump'):
                        return event.output.model_dump()
                    return event.output
                if hasattr(event, 'content') and event.content and hasattr(event.content, 'parts'):
                    for part in event.content.parts:
                        if hasattr(part, 'text') and part.text:
                            return part.text
            return None

        # 1. Intent — real-time AI
        intent_agent = get_intent_agent()
        intent_runner = InMemoryRunner(agent=intent_agent, app_name=settings.APP_NAME)
        intent_events = await intent_runner.run_debug(goal)
        raw_intent = extract_event_text(intent_events)

        if isinstance(raw_intent, dict):
            intent_result = raw_intent
        elif isinstance(raw_intent, str):
            intent_result = json.loads(raw_intent)
        else:
            intent_result = {"action": "unknown", "target": goal}

        logger.info(f"[{run_id[:8]}] Intent: {intent_result}")

        # 2. Plan — real-time AI
        planner_agent = get_planner_agent()
        planner_runner = InMemoryRunner(agent=planner_agent, app_name=settings.APP_NAME)
        plan_events = await planner_runner.run_debug(json.dumps(intent_result))
        raw_plan = extract_event_text(plan_events)

        if isinstance(raw_plan, dict):
            workflow_def = WorkflowDefinition(**raw_plan)
        elif isinstance(raw_plan, str):
            workflow_def = WorkflowDefinition(**json.loads(raw_plan))
        else:
            raise Exception(f"Planner returned unexpected output: {type(raw_plan)}")

        validate_dag(workflow_def)

        # 3. Create run with real user
        run = WorkflowRun(
            run_id=run_id, workflow_id=workflow_id,
            user_id=user.user_id, goal=goal,
            status=TaskStatus.RUNNING,
        )
        for t_def in workflow_def.tasks:
            run.tasks.append(Task(
                task_id=t_def.task_id, workflow_id=workflow_id,
                run_id=run_id, user_id=user.user_id,
                agent=t_def.agent, tool=t_def.tool,
                input_data=t_def.input_data, dependencies=t_def.dependencies,
                timeout_seconds=t_def.timeout_seconds, max_retries=t_def.max_retries,
                status=TaskStatus.PENDING,
            ))

        run_dict = run.model_dump(mode="json")
        run_dict["tasks"] = [t.model_dump(mode="json") for t in run.tasks]
        await factory.workflow_repo.save_run(run_dict)

        start_event = WorkflowEvent(
            type=WorkflowEventType.WORKFLOW_STARTED,
            workflow_id=workflow_id, run_id=run_id,
            summary=f"Workflow started for goal: {goal}",
        )
        await factory.workflow_repo.save_event(start_event.model_dump(mode="json"))

        await factory.audit_repo.log_event({
            "event_type": "WORKFLOW_CREATED",
            "actor_id": user.user_id, "actor_type": "USER",
            "resource_id": run_id, "workflow_id": workflow_id, "run_id": run_id,
            "details": {"goal": goal, "task_count": len(workflow_def.tasks)},
        })

        await workflow_engine.evaluate_dag(run_id)

        return {
            "run_id": run_id, "workflow_id": workflow_id,
            "status": run.status, "task_count": len(run.tasks),
            "message": "Workflow created and executing.",
        }

    except DAGValidationError as e:
        raise HTTPException(status_code=400, detail=f"Invalid Plan: {e}")
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════════
#  LIST / GET / EVENTS
# ══════════════════════════════════════════════════════════════════

@router.get("")
async def list_workflows(
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    limit: int = 50, offset: int = 0,
):
    """List the authenticated user's workflow runs."""
    factory = _get_factory(request)
    runs = await factory.workflow_repo.list_runs(user.user_id, limit=limit, offset=offset)
    return {"workflows": runs, "count": len(runs)}


@router.get("/{run_id}")
async def get_workflow(
    run_id: str, request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Get a workflow run with all tasks."""
    factory = _get_factory(request)
    run = await factory.workflow_repo.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if run.get("user_id") != user.user_id and not user.is_admin():
        raise HTTPException(status_code=403, detail="Access denied")
    return run


@router.get("/{run_id}/events")
async def stream_events(
    run_id: str, request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Stream workflow events via SSE with poll-based cursor."""
    factory = _get_factory(request)
    run = await factory.workflow_repo.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if run.get("user_id") != user.user_id and not user.is_admin():
        raise HTTPException(status_code=403, detail="Access denied")

    async def event_generator():
        last_event_id = None
        while True:
            if await request.is_disconnected():
                break
            events = await factory.workflow_repo.get_events(run_id, after_event_id=last_event_id)
            for event in events:
                last_event_id = event["event_id"]
                yield f"id: {event['event_id']}\ndata: {json.dumps(event)}\n\n"
            await asyncio.sleep(1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ══════════════════════════════════════════════════════════════════
#  CANCEL / RETRY
# ══════════════════════════════════════════════════════════════════

@router.post("/{run_id}/cancel", status_code=status.HTTP_200_OK)
async def cancel_workflow(
    run_id: str, request: Request,
    user: AuthenticatedUser = Depends(require_not_viewer),
):
    """Cancel a running workflow."""
    factory = _get_factory(request)
    run = await factory.workflow_repo.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if run.get("user_id") != user.user_id and not user.is_admin():
        raise HTTPException(status_code=403, detail="Access denied")

    if run.get("status") not in ("RUNNING", "PENDING"):
        raise HTTPException(status_code=400, detail=f"Cannot cancel workflow in {run.get('status')} state")

    await factory.workflow_repo.update_run_status(run_id, "CANCELLED")

    # Cancel all pending/running tasks
    for task in run.get("tasks", []):
        if task.get("status") in ("PENDING", "RUNNING", "WAITING", "RETRYING"):
            await factory.workflow_repo.update_task(
                run_id, task["task_id"], {"status": "CANCELLED"}
            )

    await factory.audit_repo.log_event({
        "event_type": "WORKFLOW_CANCELLED",
        "actor_id": user.user_id, "actor_type": "USER",
        "resource_id": run_id, "run_id": run_id,
        "details": {},
    })

    return {"run_id": run_id, "status": "CANCELLED"}


@router.post("/{run_id}/retry", status_code=status.HTTP_200_OK)
async def retry_workflow(
    run_id: str, request: Request,
    user: AuthenticatedUser = Depends(require_not_viewer),
):
    """Retry a failed workflow by re-queuing failed tasks."""
    factory = _get_factory(request)
    workflow_engine = getattr(request.app.state, "workflow_engine", None)

    run = await factory.workflow_repo.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if run.get("user_id") != user.user_id and not user.is_admin():
        raise HTTPException(status_code=403, detail="Access denied")

    if run.get("status") not in ("FAILED", "CANCELLED"):
        raise HTTPException(status_code=400, detail=f"Can only retry FAILED or CANCELLED workflows")

    # Reset failed tasks to PENDING
    retried_count = 0
    for task in run.get("tasks", []):
        if task.get("status") in ("FAILED", "CANCELLED"):
            await factory.workflow_repo.update_task(
                run_id, task["task_id"],
                {"status": "PENDING", "error": None, "error_type": None, "attempt": 0}
            )
            retried_count += 1

    await factory.workflow_repo.update_run_status(run_id, "RUNNING")

    await factory.audit_repo.log_event({
        "event_type": "WORKFLOW_RETRIED",
        "actor_id": user.user_id, "actor_type": "USER",
        "resource_id": run_id, "run_id": run_id,
        "details": {"retried_tasks": retried_count},
    })

    if workflow_engine:
        await workflow_engine.evaluate_dag(run_id)

    return {"run_id": run_id, "status": "RUNNING", "retried_tasks": retried_count}
