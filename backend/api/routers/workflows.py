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
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request, Depends, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.api.dependencies.auth import get_current_user, AuthenticatedUser, require_not_viewer
from backend.security.input_sanitizer import sanitize_goal, InputValidationError
from backend.security.rate_limiter import check_rate_limit
from backend.security.rbac import require_resource_owner
from backend.config.settings import settings
from backend.engine.repo_adapter import maybe_await

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workflows", tags=["workflows"])


def _get_factory(request: Request):
    factory = getattr(request.app.state, "factory", None)
    if not factory:
        raise HTTPException(status_code=500, detail="Server not initialized")
    return factory


class GoalAttachment(BaseModel):
    name: str = ""
    mime: str = ""
    text: Optional[str] = None
    image_base64: Optional[str] = None


class GoalRequest(BaseModel):
    goal: str
    attachments: List[GoalAttachment] = []
    parent_run_id: Optional[str] = None
    thread_id: Optional[str] = None


def _as_run_dict(run) -> Optional[dict]:
    if run is None:
        return None
    if isinstance(run, dict):
        return run
    if hasattr(run, "model_dump"):
        return run.model_dump(mode="json")
    return dict(run)


def _run_context_text(run: dict, limit: int = 3500) -> str:
    parts = [f"User: {run.get('goal') or ''}"]
    for task in run.get("tasks") or []:
        out = task.get("output_data") if isinstance(task, dict) else getattr(task, "output_data", None)
        err = task.get("error") if isinstance(task, dict) else getattr(task, "error", None)
        if isinstance(out, dict):
            for key in ("reply", "message", "summary"):
                val = out.get(key)
                if isinstance(val, str) and val.strip():
                    parts.append(f"AgentOS: {val.strip()[:1200]}")
                    break
            else:
                parts.append(f"AgentOS: {json.dumps(out, default=str)[:800]}")
        if err:
            parts.append(f"Error: {err}")
    return "\n".join(parts)[:limit]


async def _thread_runs(factory, user_id: str, thread_id: str) -> list:
    lister = getattr(factory.workflow_repo, "list_thread_runs", None)
    if callable(lister):
        return await lister(user_id, thread_id)
    runs = await factory.workflow_repo.list_runs(user_id, limit=80, offset=0)
    out = []
    for raw in runs:
        run = _as_run_dict(raw) or {}
        tid = run.get("thread_id") or run.get("run_id")
        if tid == thread_id or run.get("parent_run_id") == thread_id or run.get("run_id") == thread_id:
            out.append(run)
    out.sort(key=lambda r: str(r.get("created_at") or ""))
    return out


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
    from backend.services.llm_context import load_user_llm_keys
    await load_user_llm_keys(factory.secrets_repo, user.user_id)

    try:
        goal = sanitize_goal(body.goal)
    except InputValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)

    extra_parts: list[str] = []
    for att in (body.attachments or [])[:5]:
        name = (att.name or "attachment")[:200]
        mime = (att.mime or "")[:120]
        if att.text:
            extra_parts.append(f"Attached file `{name}`:\n{(att.text or '')[:12000]}")
        elif att.image_base64:
            try:
                import base64
                from backend.services import gemini_client
                raw = base64.b64decode(att.image_base64, validate=False)
                if len(raw) > 4 * 1024 * 1024:
                    extra_parts.append(f"Attached photo `{name}` was skipped (larger than 4 MB).")
                else:
                    desc = await gemini_client.describe_image(raw, mime or "image/jpeg", name)
                    extra_parts.append(f"Attached photo `{name}`:\n{desc[:8000]}")
            except Exception as exc:
                logger.warning("Could not describe photo %s: %s", name, exc)
                extra_parts.append(f"Attached photo `{name}` ({mime or 'image'}).")
        else:
            extra_parts.append(f"Attached file `{name}` ({mime or 'file'}).")
    if extra_parts:
        goal = (goal + "\n\n" + "\n\n".join(extra_parts)).strip()[:40000]

    if not goal:
        raise HTTPException(status_code=400, detail="Goal cannot be empty")

    parent = None
    if body.parent_run_id:
        parent = _as_run_dict(await factory.workflow_repo.get_run(body.parent_run_id))
        if not parent or (parent.get("user_id") != user.user_id and not user.is_admin()):
            raise HTTPException(status_code=400, detail="Invalid parent conversation.")

    run_id = str(uuid.uuid4())
    workflow_id = f"wf-{run_id[:8]}"
    thread_id = body.thread_id or (parent.get("thread_id") if parent else None) or (parent.get("run_id") if parent else run_id)

    try:
        from backend.models.schemas import (
            WorkflowRun, Task, TaskStatus, WorkflowDefinition,
            WorkflowEvent, WorkflowEventType,
        )
        from backend.engine.dag_validator import prepare_dag, enrich_plan_from_intent, DAGValidationError
        from backend.engine.direct_plan import plan_from_goal

        tool_router = getattr(request.app.state, "tool_router", None)
        live_catalog = await tool_router.get_tool_catalog(user.user_id) if tool_router else []
        workflow_def = plan_from_goal(
            goal,
            prior_goal=(parent.get("goal") if parent else "") or "",
            catalog=live_catalog,
        )
        if workflow_def:
            logger.info("[%s] Direct plan for goal (no Gemini planner)", run_id[:8])
        else:
            from backend.agents.intent.intent_agent import get_intent_agent
            from backend.agents.planner.planner_agent import get_planner_agent
            from backend.services import gemini_client

            def extract_event_text(events):
                for event in reversed(events):
                    if event.output is not None:
                        if hasattr(event.output, "model_dump"):
                            return event.output.model_dump()
                        return event.output
                    if hasattr(event, "content") and event.content and hasattr(event.content, "parts"):
                        for part in event.content.parts:
                            if hasattr(part, "text") and part.text:
                                return part.text
                return None

            intent_events = await gemini_client.run_adk_debug(
                lambda model: get_intent_agent(model=model),
                goal,
                settings.APP_NAME,
            )
            raw_intent = extract_event_text(intent_events)

            if isinstance(raw_intent, dict):
                intent_result = raw_intent
            elif isinstance(raw_intent, str):
                intent_result = json.loads(raw_intent)
            else:
                intent_result = {"action": "unknown", "target": goal}

            logger.info(f"[{run_id[:8]}] Intent: {intent_result}")

            catalog_blob = json.dumps(live_catalog)
            plan_events = await gemini_client.run_adk_debug(
                lambda model: get_planner_agent(catalog_json=catalog_blob, model=model),
                json.dumps(intent_result),
                settings.APP_NAME,
            )
            raw_plan = extract_event_text(plan_events)

            if isinstance(raw_plan, dict):
                workflow_def = WorkflowDefinition(**raw_plan)
            elif isinstance(raw_plan, str):
                workflow_def = WorkflowDefinition(**json.loads(raw_plan))
            else:
                raise Exception(f"Planner returned unexpected output: {type(raw_plan)}")

            workflow_def = enrich_plan_from_intent(workflow_def, intent_result, live_catalog, goal=goal)

        if parent and workflow_def:
            ctx = _run_context_text(parent)
            for t_def in workflow_def.tasks:
                if t_def.agent == "core.chat":
                    prompt = str((t_def.input_data or {}).get("prompt") or goal)
                    t_def.input_data = {
                        **(t_def.input_data or {}),
                        "prompt": f"Earlier in this conversation:\n{ctx}\n\nNew message:\n{prompt}",
                    }

        prepare_dag(workflow_def)

        # 3. Create run with real user
        run = WorkflowRun(
            run_id=run_id, workflow_id=workflow_id,
            user_id=user.user_id, goal=goal,
            status=TaskStatus.RUNNING,
            parent_run_id=body.parent_run_id,
            thread_id=thread_id,
        )
        for t_def in workflow_def.tasks:
            run.tasks.append(Task(
                task_id=t_def.task_id, workflow_id=workflow_id,
                run_id=run_id, user_id=user.user_id,
                agent=t_def.agent, tool=t_def.tool,
                input_data=t_def.input_data, dependencies=t_def.dependencies,
                timeout_seconds=max(t_def.timeout_seconds, 180) if t_def.agent in ("Orchestrator", "OrchestratorAgent", "core.mcp_build") or "orchestrator" in (t_def.agent or "").lower() else t_def.timeout_seconds,
                max_retries=t_def.max_retries,
                recovery_enabled=True,
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
            "thread_id": thread_id,
            "parent_run_id": body.parent_run_id,
            "message": "Workflow created and executing.",
        }

    except DAGValidationError as e:
        raise HTTPException(status_code=400, detail=f"Invalid Plan: {e}")
    except Exception as e:
        traceback.print_exc()
        msg = str(e)
        if "RESOURCE_EXHAUSTED" in msg or "429" in msg or "quota exhausted" in msg.lower() or "UNAUTHENTICATED" in msg or "API_KEY_INVALID" in msg:
            raise HTTPException(
                status_code=429,
                detail=(
                    "Gemini quota is exhausted for this kind of goal. Add your own key in Settings, "
                    "or try a live action that does not need the planner: "
                    "check the health of https://example.com, GET a public HTTPS URL, "
                    "or build an MCP from an OpenAPI spec."
                ),
            )
        raise HTTPException(status_code=500, detail=msg)


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


@router.get("/{run_id}/thread")
async def get_workflow_thread(
    run_id: str, request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
):
    factory = _get_factory(request)
    run = _as_run_dict(await factory.workflow_repo.get_run(run_id))
    if not run:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if run.get("user_id") != user.user_id and not user.is_admin():
        raise HTTPException(status_code=403, detail="Forbidden")
    thread_id = run.get("thread_id") or run.get("parent_run_id") or run_id
    workflows = await _thread_runs(factory, user.user_id, thread_id)
    if not any(w.get("run_id") == run_id for w in workflows):
        workflows.append(run)
        workflows.sort(key=lambda r: str(r.get("created_at") or ""))
    return {"thread_id": thread_id, "workflows": workflows}


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
        try:
            yield ": connected\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    events = await factory.workflow_repo.get_events(run_id, after_event_id=last_event_id)
                except Exception as exc:
                    logger.exception("SSE get_events failed for run %s", run_id)
                    yield f"event: error\ndata: {json.dumps({'error': str(exc)[:800]})}\n\n"
                    return
                for event in events:
                    last_event_id = event.get("event_id")
                    yield f"id: {last_event_id}\ndata: {json.dumps(event, default=str)}\n\n"
                await asyncio.sleep(1)
        except Exception as exc:
            logger.exception("SSE stream failed for run %s", run_id)
            yield f"event: error\ndata: {json.dumps({'error': str(exc)[:800]})}\n\n"

    origin = request.headers.get("origin") or ""
    cors = {}
    if origin in settings.CORS_ALLOWED_ORIGINS:
        cors = {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
            "Vary": "Origin",
        }
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            **cors,
        },
    )


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

    if run.get("status") == "CANCELLED":
        return {"run_id": run_id, "status": "CANCELLED"}
    if run.get("status") not in ("RUNNING", "PENDING"):
        return {"run_id": run_id, "status": run.get("status")}

    await factory.workflow_repo.update_run_status(run_id, "CANCELLED")

    # Cancel all pending/running tasks
    for task in run.get("tasks", []):
        if task.get("status") in ("PENDING", "RUNNING", "WAITING", "RETRYING", "WAITING_APPROVAL"):
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


@router.post("/{run_id}/resume", status_code=status.HTTP_200_OK)
async def resume_workflow(
    run_id: str, request: Request,
    user: AuthenticatedUser = Depends(require_not_viewer),
):
    """Resume tasks paused for human approval (CAPTCHA/OTP/MFA or risk gate)."""
    factory = _get_factory(request)
    workflow_engine = getattr(request.app.state, "workflow_engine", None)
    run = await factory.workflow_repo.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if run.get("user_id") != user.user_id and not user.is_admin():
        raise HTTPException(status_code=403, detail="Access denied")

    resumed = 0
    for task in run.get("tasks", []):
        if task.get("status") != "WAITING_APPROVAL":
            continue
        await factory.workflow_repo.update_task(
            run_id, task["task_id"],
            {"status": "PENDING", "error": None},
        )
        resumed += 1
        try:
            approvals = await maybe_await(factory.workflow_repo.list_pending_approvals(user.user_id))
            for approval in approvals or []:
                aid = approval.get("approval_id") if isinstance(approval, dict) else getattr(approval, "approval_id", None)
                tid = approval.get("task_id") if isinstance(approval, dict) else getattr(approval, "task_id", None)
                rid = approval.get("run_id") if isinstance(approval, dict) else getattr(approval, "run_id", None)
                if rid == run_id and tid == task["task_id"] and aid:
                    from backend.models.security import ApprovalStatus
                    await maybe_await(factory.workflow_repo.resolve_approval(
                        aid, ApprovalStatus.APPROVED.value, decision_by=user.user_id
                    ))
        except Exception:
            logger.exception("Could not auto-resolve approval on resume")

    if resumed == 0:
        raise HTTPException(status_code=400, detail="No paused tasks to resume")

    await factory.workflow_repo.update_run_status(run_id, "RUNNING")
    if workflow_engine:
        await workflow_engine.evaluate_dag(run_id)
    return {"run_id": run_id, "status": "RUNNING", "resumed_tasks": resumed}
