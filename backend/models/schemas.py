from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Any, Dict
from datetime import datetime, timezone
from enum import Enum
import uuid

class GeminiCompatibleBaseModel(BaseModel):
    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema, handler):
        json_schema = handler(core_schema)
        json_schema = handler.resolve_ref_schema(json_schema)
        def clean(d):
            if isinstance(d, dict):
                d.pop("additionalProperties", None)
                for k, v in list(d.items()):
                    clean(v)
            elif isinstance(d, list):
                for item in d:
                    clean(item)
            return d
        return clean(json_schema)

class TaskStatus(str):
    PENDING = "PENDING"
    WAITING = "WAITING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    RETRYING = "RETRYING"
    CANCELLED = "CANCELLED"
    BLOCKED = "BLOCKED"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    RECOVERING = "RECOVERING"
    SKIPPED = "SKIPPED"

class ErrorType(str, Enum):
    SEMANTIC_ERROR = "SEMANTIC_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    TRANSIENT_ERROR = "TRANSIENT_ERROR"
    AUTHORIZATION_ERROR = "AUTHORIZATION_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"

class SemanticErrorReason(str, Enum):
    INVALID_ARGUMENT = "INVALID_ARGUMENT"
    SCHEMA_MISMATCH = "SCHEMA_MISMATCH"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    INVALID_ENUM = "INVALID_ENUM"
    TYPE_MISMATCH = "TYPE_MISMATCH"
    INVALID_PARAMETER_FORMAT = "INVALID_PARAMETER_FORMAT"
    TOOL_SEMANTIC_REJECTION = "TOOL_SEMANTIC_REJECTION"

class TaskDefinition(GeminiCompatibleBaseModel):
    task_id: str = Field(description="Unique identifier for the task within the workflow")
    agent: str = Field(description="The agent to handle the task")
    tool: Optional[str] = Field(None, description="The tool to execute, if any")
    input_data: Dict[str, Any] = Field(default_factory=dict, description="Input parameters")
    dependencies: List[str] = Field(default_factory=list, description="IDs of tasks that must complete first")
    timeout_seconds: int = Field(60, description="Execution timeout in seconds")
    max_retries: int = Field(3, description="Maximum number of retry attempts")

class WorkflowDefinition(GeminiCompatibleBaseModel):
    tasks: List[TaskDefinition] = Field(description="The list of tasks in the workflow")

class Task(BaseModel):
    task_id: str
    workflow_id: str
    run_id: str
    user_id: str = "default_user"
    agent: str
    tool: Optional[str] = None
    status: str = TaskStatus.PENDING
    input_data: Dict[str, Any] = Field(default_factory=dict)
    output_data: Optional[Dict[str, Any]] = None
    dependencies: List[str] = Field(default_factory=list)
    
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    lease_started_at: Optional[datetime] = None
    lease_expires_at: Optional[datetime] = None
    attempt: int = 0
    timeout_seconds: int = 60
    max_retries: int = 3
    
    # Phase 11: Self-Healing
    recovery_enabled: bool = False
    max_recoveries: int = 3
    max_total_attempts: int = 5
    recovery_attempts: int = 0
    original_input: Optional[Dict[str, Any]] = None
    recovery_history: List[Dict[str, Any]] = Field(default_factory=list)
    
    error: Optional[str] = None
    error_type: Optional[str] = None
    trace_id: Optional[str] = None

class WorkflowRun(BaseModel):
    run_id: str
    workflow_id: str = "default_workflow"
    user_id: str = "default_user"
    goal: str
    status: str = TaskStatus.PENDING
    tasks: List[Task] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class IntentSchema(GeminiCompatibleBaseModel):
    action: str = Field(description="The core action the user wants to perform")
    target: str = Field(description="The target of the action")
    context: Optional[str] = Field(None, description="Any additional context provided")

class TaskTriggerEvent(BaseModel):
    workflow_id: str
    run_id: str
    task_id: str
    trace_id: Optional[str] = None

class TaskRecoveryEvent(BaseModel):
    workflow_id: str
    run_id: str
    task_id: str
    recovery_attempt: int
    trace_id: Optional[str] = None

class WorkflowEventType(str, Enum):
    WORKFLOW_STARTED = "WORKFLOW_STARTED"
    WORKFLOW_COMPLETED = "WORKFLOW_COMPLETED"
    WORKFLOW_FAILED = "WORKFLOW_FAILED"
    TASK_STARTED = "TASK_STARTED"
    TASK_COMPLETED = "TASK_COMPLETED"
    TASK_FAILED = "TASK_FAILED"
    TASK_RETRYING = "TASK_RETRYING"
    TASK_RECOVERING = "TASK_RECOVERING"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    APPROVAL_GRANTED = "APPROVAL_GRANTED"
    APPROVAL_REJECTED = "APPROVAL_REJECTED"
    TOOL_INVOKED = "TOOL_INVOKED"
    TOOL_COMPLETED = "TOOL_COMPLETED"

class WorkflowEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    type: str  # WorkflowEventType
    workflow_id: str
    run_id: str
    task_id: Optional[str] = None
    status: Optional[str] = None
    summary: str
    sanitized_metadata: Dict[str, Any] = Field(default_factory=dict)

