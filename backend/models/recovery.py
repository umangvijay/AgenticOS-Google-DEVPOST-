from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from backend.models.schemas import SemanticErrorReason
from enum import Enum

class RecoveryActionEnum(str, Enum):
    REPAIR = "REPAIR"
    ABORT = "ABORT"

class RecoveryAction(BaseModel):
    action: str = Field(description="Must be REPAIR or ABORT.")
    corrected_input: Optional[Dict[str, Any]] = Field(None, description="The corrected input arguments if action is REPAIR. Must strictly adhere to the original tool schema.")
    rationale: str = Field(description="Explanation of why the error occurred and how this action fixes it.")
    expected_error_resolved: Optional[str] = Field(None, description="The specific error or validation issue this repair is expected to resolve.")

class RecoveryContext(BaseModel):
    workflow_id: str
    run_id: str
    task_id: str
    task_type: str
    original_input: Dict[str, Any]
    current_input: Dict[str, Any]
    validation_error: str
    error_reason: SemanticErrorReason
    allowed_tool_schema: Optional[Dict[str, Any]] = None
    previous_recovery_attempts: int
    safe_error_details: str
