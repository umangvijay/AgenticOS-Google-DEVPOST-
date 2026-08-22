from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Any, Dict
from datetime import datetime, timezone

class TaskStatus(str):
    PENDING = "PENDING"
    WAITING = "WAITING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    RETRYING = "RETRYING"
    CANCELLED = "CANCELLED"
    BLOCKED = "BLOCKED"

class ErrorType(str):
    RETRYABLE = "RETRYABLE"
    NON_RETRYABLE = "NON_RETRYABLE"

class TaskDefinition(BaseModel):
    task_id: str = Field(description="Unique identifier for the task within the workflow")
    agent: str = Field(description="The agent to handle the task")
    tool: Optional[str] = Field(None, description="The tool to execute, if any")
    input_data: Dict[str, Any] = Field(default_factory=dict, description="Input parameters")
    dependencies: List[str] = Field(default_factory=list, description="IDs of tasks that must complete first")
    timeout_seconds: int = Field(60, description="Execution timeout in seconds")
    max_retries: int = Field(3, description="Maximum number of retry attempts")

class WorkflowDefinition(BaseModel):
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

class IntentSchema(BaseModel):
    action: str = Field(description="The core action the user wants to perform")
    target: str = Field(description="The target of the action")
    context: Optional[str] = Field(None, description="Any additional context provided")

class TaskTriggerEvent(BaseModel):
    workflow_id: str
    run_id: str
    task_id: str
    trace_id: Optional[str] = None
