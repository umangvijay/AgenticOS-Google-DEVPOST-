import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from backend.models.security import ApprovalRequest, ApprovalStatus
from backend.repositories.workflow_repository import WorkflowRepository
from backend.repositories.message_bus import MessageBus
from backend.models.schemas import TaskTriggerEvent, TaskStatus
from backend.api.dependencies.auth import get_current_user
from backend.repositories.audit_repository import audit_repo, AuditEvent

logger = logging.getLogger(__name__)

# Note: In a real app, these dependencies would be injected or fetched from app state.
# We'll assume they can be fetched similarly to other endpoints.
# For simplicity, we define a stub getter.
def get_workflow_repo() -> WorkflowRepository:
    import backend.api.main as main
    if not main.workflow_repo:
        raise HTTPException(status_code=500, detail="Repository not initialized")
    return main.workflow_repo

def get_message_bus() -> MessageBus:
    import backend.api.main as main
    if not main.message_bus:
        raise HTTPException(status_code=500, detail="Message bus not initialized")
    return main.message_bus

router = APIRouter(prefix="/approvals", tags=["approvals"])

@router.get("", response_model=List[ApprovalRequest])
async def list_approvals(
    user_id: str = Depends(get_current_user),
    repo: WorkflowRepository = Depends(get_workflow_repo)
):
    """List all pending approvals for the authenticated user."""
    return repo.list_pending_approvals(user_id)

@router.post("/{approval_id}/approve")
async def approve_request(
    approval_id: str,
    user_id: str = Depends(get_current_user),
    repo: WorkflowRepository = Depends(get_workflow_repo),
    bus: MessageBus = Depends(get_message_bus)
):
    """Approve a pending request and resume the workflow."""
    approval = repo.get_approval(approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")
        
    # Enforce ownership
    if approval.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this approval")
        
    # Atomic resolution
    success = repo.resolve_approval(approval_id, ApprovalStatus.APPROVED.value, decision_by=user_id)
    if not success:
        raise HTTPException(status_code=409, detail="Approval already resolved or not pending")
        
    # Resume the workflow task
    event = TaskTriggerEvent(
        workflow_id=approval.workflow_id,
        run_id=approval.run_id,
        task_id=approval.task_id
    )
    
    # We must also fetch the task and transition it back to PENDING so the worker can claim it
    run = repo.get_run(approval.run_id)
    if run:
        for t in run.tasks:
            if t.task_id == approval.task_id and t.status == TaskStatus.WAITING_APPROVAL:
                # We need to inject the approved request into the task so ToolRouter can use it
                t.status = TaskStatus.PENDING
                t.input_data["_approved_request_id"] = approval_id
                repo.update_task(run.run_id, t)
                break
                
    from backend.repositories.audit_repository import ActorType
    audit_repo.log_event(AuditEvent(
        event_type="APPROVAL_GRANTED",
        actor_id=user_id,
        actor_type=ActorType.USER,
        resource_id=approval_id,
        workflow_id=approval.workflow_id,
        run_id=approval.run_id,
        task_id=approval.task_id,
        details={"workflow_id": approval.workflow_id, "task_id": approval.task_id}
    ))
                
    await bus.publish("agentos-workflow-events", event)
    
    return {"status": "success", "message": "Approval granted"}

@router.post("/{approval_id}/reject")
async def reject_request(
    approval_id: str,
    user_id: str = Depends(get_current_user),
    repo: WorkflowRepository = Depends(get_workflow_repo),
    bus: MessageBus = Depends(get_message_bus)
):
    """Reject a pending request, causing the workflow task to fail."""
    approval = repo.get_approval(approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")
        
    if approval.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this approval")
        
    success = repo.resolve_approval(approval_id, ApprovalStatus.REJECTED.value, decision_by=user_id)
    if not success:
        raise HTTPException(status_code=409, detail="Approval already resolved or not pending")
        
    # Resume the task so it fails
    run = repo.get_run(approval.run_id)
    if run:
        for t in run.tasks:
            if t.task_id == approval.task_id and t.status == TaskStatus.WAITING_APPROVAL:
                t.status = TaskStatus.FAILED
                t.error = "Human approval rejected"
                repo.update_task(run.run_id, t)
                break
                
    from backend.repositories.audit_repository import ActorType
    audit_repo.log_event(AuditEvent(
        event_type="APPROVAL_REJECTED",
        actor_id=user_id,
        actor_type=ActorType.USER,
        resource_id=approval_id,
        workflow_id=approval.workflow_id,
        run_id=approval.run_id,
        task_id=approval.task_id,
        details={"workflow_id": approval.workflow_id, "task_id": approval.task_id}
    ))
                
    # We don't trigger the task itself since we failed it, but we should trigger DAG evaluation
    # to cascade the failure or cancel downstream tasks.
    # For now, we publish a resume event just in case, or we could publish a different event.
    # The simplest is triggering DAG evaluation directly or by an event.
    
    return {"status": "success", "message": "Approval rejected"}
