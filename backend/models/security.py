import hashlib
import json
from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, Any, Dict
from datetime import datetime, timezone

class RiskLevel(int, Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

class AutonomyLevel(int, Enum):
    L0_MANUAL = 0            # All require approval
    L1_SUPERVISED = 1        # LOW automatic
    L2_SEMI_AUTONOMOUS = 2   # LOW, MEDIUM automatic
    L3_AUTONOMOUS = 3        # LOW, MEDIUM, HIGH automatic; CRITICAL requires approval

class ApprovalStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"

class ApprovalRequest(BaseModel):
    approval_id: str
    user_id: str
    tool_name: str
    tool_version: str
    risk_level: RiskLevel
    autonomy_level: AutonomyLevel
    arguments: Dict[str, Any]
    arguments_hash: str
    workflow_id: str
    run_id: str
    task_id: str
    requested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime
    requested_by: str = "system"
    status: ApprovalStatus = ApprovalStatus.PENDING
    decision_by: Optional[str] = None
    decision_at: Optional[datetime] = None
    
    @classmethod
    def compute_arguments_hash(cls, arguments: dict) -> str:
        """Compute a deterministic hash of the tool arguments."""
        # Sort keys to ensure deterministic JSON stringification
        serialized = json.dumps(arguments, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(serialized.encode('utf-8')).hexdigest()
