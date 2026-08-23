from datetime import datetime, timezone, timedelta
from typing import Dict, Any
from backend.models.security import RiskLevel, AutonomyLevel, ApprovalRequest, ApprovalStatus
from backend.repositories.audit_repository import audit_repo, AuditEvent
import uuid

class ApprovalRequiredException(Exception):
    def __init__(self, message: str, pending_approval: ApprovalRequest):
        super().__init__(message)
        self.pending_approval = pending_approval

class ApprovalsEngine:
    def __init__(self):
        # We define the threshold matrix here.
        # If risk > autonomy_level (mapped to integer), approval is required.
        pass
        
    def requires_approval(self, autonomy_level: AutonomyLevel, risk_level: RiskLevel) -> bool:
        """
        Evaluates whether a given risk level requires approval under a specific autonomy level.
        L0_MANUAL: All require approval.
        L1_SUPERVISED: LOW automatic.
        L2_SEMI_AUTONOMOUS: LOW, MEDIUM automatic.
        L3_AUTONOMOUS: LOW, MEDIUM, HIGH automatic; CRITICAL requires approval.
        """
        # CRITICAL always requires approval
        if risk_level == RiskLevel.CRITICAL:
            return True
            
        # Map Autonomy to max allowed risk
        max_allowed = {
            AutonomyLevel.L0_MANUAL: 0, # nothing
            AutonomyLevel.L1_SUPERVISED: RiskLevel.LOW.value,
            AutonomyLevel.L2_SEMI_AUTONOMOUS: RiskLevel.MEDIUM.value,
            AutonomyLevel.L3_AUTONOMOUS: RiskLevel.HIGH.value
        }
        
        return risk_level.value > max_allowed[autonomy_level]
        
    def create_approval_request(self, user_id: str, tool_name: str, tool_version: str, 
                                risk_level: RiskLevel, autonomy_level: AutonomyLevel, 
                                arguments: Dict[str, Any], workflow_id: str, 
                                run_id: str, task_id: str) -> ApprovalRequest:
        """
        Creates a new ApprovalRequest with a computed argument hash and expiry.
        """
        args_hash = ApprovalRequest.compute_arguments_hash(arguments)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=24) # 24 hour expiry
        
        req = ApprovalRequest(
            approval_id=str(uuid.uuid4()),
            user_id=user_id,
            tool_name=tool_name,
            tool_version=tool_version,
            risk_level=risk_level,
            autonomy_level=autonomy_level,
            arguments=arguments,
            arguments_hash=args_hash,
            workflow_id=workflow_id,
            run_id=run_id,
            task_id=task_id,
            expires_at=expires_at,
            status=ApprovalStatus.PENDING
        )
        
        from backend.repositories.audit_repository import ActorType
        audit_repo.log_event(AuditEvent(
            event_type="APPROVAL_REQUESTED",
            actor_id="SYSTEM",
            actor_type=ActorType.SYSTEM,
            resource_id=req.approval_id,
            workflow_id=workflow_id,
            run_id=run_id,
            task_id=task_id,
            details={
                "tool_name": tool_name,
                "risk_level": risk_level.name,
                "autonomy_level": autonomy_level.name,
                "task_id": task_id
            }
        ))
        
        return req
        
    def validate_approval_for_execution(self, approval: ApprovalRequest, current_arguments: Dict[str, Any]) -> None:
        """
        Validates that a resolved approval is still valid for execution.
        Raises ValueError if the approval is invalid.
        """
        if approval.status != ApprovalStatus.APPROVED:
            raise ValueError(f"Approval is in state {approval.status.value}, expected APPROVED")
            
        if datetime.now(timezone.utc) > approval.expires_at:
            # Mark it expired logically, or raise
            raise ValueError("Approval has expired")
            
        # Exact-action binding verification
        from backend.repositories.audit_repository import ActorType
        current_hash = ApprovalRequest.compute_arguments_hash(current_arguments)
        if current_hash != approval.arguments_hash:
            audit_repo.log_event(AuditEvent(
                event_type="APPROVAL_VALIDATION_FAILED",
                actor_id="SYSTEM",
                actor_type=ActorType.SYSTEM,
                resource_id=approval.approval_id,
                workflow_id=approval.workflow_id,
                run_id=approval.run_id,
                task_id=approval.task_id,
                details={"reason": "Arguments changed (TOCTOU violation)"}
            ))
            raise ValueError("Arguments have changed since approval was granted (TOCTOU violation)")
            
        audit_repo.log_event(AuditEvent(
            event_type="APPROVAL_VALIDATED",
            actor_id="SYSTEM",
            actor_type=ActorType.SYSTEM,
            resource_id=approval.approval_id,
            workflow_id=approval.workflow_id,
            run_id=approval.run_id,
            task_id=approval.task_id,
            details={"task_id": approval.task_id}
        ))
