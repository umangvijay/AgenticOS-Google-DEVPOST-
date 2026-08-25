from fastapi import APIRouter, Request, HTTPException, Depends
from typing import Dict, Any
from backend.repositories.workflow_repository import WorkflowRepository
from backend.repositories.message_bus import MessageBus
from backend.models.schemas import WorkflowRun, Task, TaskStatus, WorkflowEventType
import uuid
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

# Simple dependency injection (in real app this would come from app state)
def get_workflow_repo() -> WorkflowRepository:
    from backend.api.main import app
    return app.state.workflow_repo

def get_message_bus() -> MessageBus:
    from backend.api.main import app
    return app.state.message_bus

@router.post("/{workflow_id}")
async def trigger_webhook(
    workflow_id: str,
    request: Request,
    repo: WorkflowRepository = Depends(get_workflow_repo),
    bus: MessageBus = Depends(get_message_bus)
):
    """
    Webhook trigger for workflows.
    Injects the webhook payload as the initial context of the workflow.
    """
    try:
        payload = await request.json()
    except Exception:
        payload = {}
        
    # In a real system, we'd fetch the WorkflowDefinition by ID
    # For this demo, we'll construct a default WorkflowRun assuming the webhook starts it.
    run_id = str(uuid.uuid4())
    
    # We create a dummy initial task that "received" the webhook data,
    # so downstream tasks can access it via {{ tasks.webhook.output.data }}
    webhook_task = Task(
        task_id="webhook",
        workflow_id=workflow_id,
        run_id=run_id,
        agent="core.set",
        status=TaskStatus.COMPLETED,
        input_data={"fields": payload},
        output_data=payload
    )
    
    run = WorkflowRun(
        run_id=run_id,
        workflow_id=workflow_id,
        goal=f"Triggered via Webhook",
        status=TaskStatus.COMPLETED,  # Dummy status since we don't have real tasks attached
        tasks=[webhook_task]
    )
    
    repo.save_run(run)
    logger.info(f"Webhook triggered workflow {workflow_id}, run_id: {run_id}")
    
    # Ideally, we would evaluate DAG here if we attached other tasks
    
    return {"message": "Webhook received", "run_id": run_id, "data": payload}
