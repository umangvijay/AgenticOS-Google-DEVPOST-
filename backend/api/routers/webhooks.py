"""
AgentOS — Webhooks Router

POST /api/v1/webhooks/{schedule_or_goal_id} — External trigger.
If the id matches one of the caller's schedules, its goal is executed with the
webhook payload injected as the root task's output ({{ tasks.webhook.output.* }}).
"""

import uuid
import logging

from fastapi import APIRouter, Request, HTTPException

from backend.models.schemas import WorkflowRun, Task, TaskStatus
from backend.engine.repo_adapter import persist_run

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/{schedule_id}")
async def trigger_webhook(schedule_id: str, request: Request):
    """
    Webhook trigger: starts the goal attached to the given schedule,
    with the webhook payload available to all tasks via interpolation.
    """
    factory = getattr(request.app.state, "factory", None)
    workflow_engine = getattr(request.app.state, "workflow_engine", None)
    if not factory or not workflow_engine:
        raise HTTPException(status_code=500, detail="Server not initialized")

    schedule = await factory.schedule_repo.get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="No trigger registered with this id")
    if str(schedule.get("status", "")).upper() != "ACTIVE":
        raise HTTPException(status_code=409, detail="Trigger is paused")

    try:
        payload = await request.json()
    except Exception:
        payload = {}

    run_id = str(uuid.uuid4())
    workflow_id = f"wh-{run_id[:8]}"

    webhook_task = Task(
        task_id="webhook",
        workflow_id=workflow_id,
        run_id=run_id,
        user_id=schedule["user_id"],
        agent="core.set",
        status=TaskStatus.COMPLETED,
        input_data={"fields": payload},
        output_data=payload,
    )
    root_task = Task(
        task_id=f"root-{run_id[:8]}",
        workflow_id=workflow_id,
        run_id=run_id,
        user_id=schedule["user_id"],
        agent="OrchestratorAgent",
        input_data={"goal": schedule["goal"], "webhook_payload": payload},
        status=TaskStatus.PENDING,
        dependencies=["webhook"],
    )

    run = WorkflowRun(
        run_id=run_id,
        workflow_id=workflow_id,
        user_id=schedule["user_id"],
        goal=schedule["goal"],
        status=TaskStatus.RUNNING,
        tasks=[webhook_task, root_task],
    )
    await persist_run(factory.workflow_repo, run)
    logger.info(f"Webhook triggered schedule {schedule_id}, run {run_id}")

    await workflow_engine.evaluate_dag(run_id)

    return {"message": "Webhook received", "run_id": run_id, "workflow_id": workflow_id}
