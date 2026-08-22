import pytest
from datetime import datetime, timezone, timedelta
from backend.models.security import RiskLevel, AutonomyLevel, ApprovalRequest, ApprovalStatus
from backend.services.approvals_engine import ApprovalsEngine, ApprovalRequiredException
from backend.repositories.workflow_repository import InMemoryWorkflowRepository
from backend.models.schemas import WorkflowRun, Task, TaskStatus

def test_autonomy_matrix():
    engine = ApprovalsEngine()
    
    # L0 Manual: Everything requires approval
    assert engine.requires_approval(AutonomyLevel.L0_MANUAL, RiskLevel.LOW) == True
    assert engine.requires_approval(AutonomyLevel.L0_MANUAL, RiskLevel.CRITICAL) == True
    
    # L1 Supervised: LOW is automatic
    assert engine.requires_approval(AutonomyLevel.L1_SUPERVISED, RiskLevel.LOW) == False
    assert engine.requires_approval(AutonomyLevel.L1_SUPERVISED, RiskLevel.MEDIUM) == True
    
    # L3 Autonomous: CRITICAL still requires approval
    assert engine.requires_approval(AutonomyLevel.L3_AUTONOMOUS, RiskLevel.HIGH) == False
    assert engine.requires_approval(AutonomyLevel.L3_AUTONOMOUS, RiskLevel.CRITICAL) == True

def test_exact_action_binding():
    engine = ApprovalsEngine()
    
    original_args = {"document_id": "123", "force": True}
    req = engine.create_approval_request(
        user_id="u1", tool_name="delete_doc", tool_version="1.0",
        risk_level=RiskLevel.HIGH, autonomy_level=AutonomyLevel.L2_SEMI_AUTONOMOUS,
        arguments=original_args, workflow_id="w1", run_id="r1", task_id="t1"
    )
    
    # Approve it
    req.status = ApprovalStatus.APPROVED
    
    # Validation with exact args should pass
    engine.validate_approval_for_execution(req, original_args)
    
    # Validation with altered args should fail
    altered_args = {"document_id": "456", "force": True}
    with pytest.raises(ValueError, match="Arguments have changed"):
        engine.validate_approval_for_execution(req, altered_args)

def test_atomic_approval_transitions():
    repo = InMemoryWorkflowRepository()
    
    run = WorkflowRun(run_id="r1", goal="test")
    task = Task(task_id="t1", workflow_id="w1", run_id="r1", agent="a")
    run.tasks.append(task)
    repo.save_run(run)
    
    engine = ApprovalsEngine()
    req = engine.create_approval_request(
        user_id="u1", tool_name="del", tool_version="1",
        risk_level=RiskLevel.CRITICAL, autonomy_level=AutonomyLevel.L3_AUTONOMOUS,
        arguments={}, workflow_id="w1", run_id="r1", task_id="t1"
    )
    
    repo.update_task(run.run_id, task, pending_approval=req)
    
    # Resolve to APPROVED
    assert repo.resolve_approval(req.approval_id, ApprovalStatus.APPROVED.value, "u1") == True
    
    # Resolving again should fail (atomic compare-and-set)
    assert repo.resolve_approval(req.approval_id, ApprovalStatus.REJECTED.value, "u2") == False
    
    fetched = repo.get_approval(req.approval_id)
    assert fetched.status == ApprovalStatus.APPROVED
    
def test_approval_expiry():
    engine = ApprovalsEngine()
    req = engine.create_approval_request(
        user_id="u1", tool_name="test", tool_version="1",
        risk_level=RiskLevel.HIGH, autonomy_level=AutonomyLevel.L3_AUTONOMOUS,
        arguments={}, workflow_id="w1", run_id="r1", task_id="t1"
    )
    req.status = ApprovalStatus.APPROVED
    
    # Force expiry
    req.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    
    with pytest.raises(ValueError, match="Approval has expired"):
        engine.validate_approval_for_execution(req, {})
