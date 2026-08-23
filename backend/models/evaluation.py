from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Optional

class AgentEvaluationRecord(BaseModel):
    evaluation_id: str
    run_id: str
    workflow_id: str
    agent_name: str
    model: str
    task_type: str
    
    # Core Outcomes
    success: bool
    recovery_attempts: int
    successful_recoveries: int
    
    # Tool accuracy
    tool_calls: int
    unknown_tool_call_rate: float = 0.0
    invalid_argument_rate: float = 0.0
    tool_schema_violation_rate: float = 0.0
    
    # Latency & Cost
    latency_ms: float
    token_usage_input: int
    token_usage_output: int
    token_usage_total: int
    
    # Approvals
    approval_latency_ms: Optional[float] = None
    rejection_rate: Optional[float] = None
    
    # Versioning
    evaluator_version: str = "1.0.0"
    prompt_version: str = "1.0.0"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
