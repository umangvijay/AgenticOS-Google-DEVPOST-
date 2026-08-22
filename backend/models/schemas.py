from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from datetime import datetime

class TaskStatus(str):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class Task(BaseModel):
    task_id: str
    workflow_id: str
    name: str
    agent: str
    status: str = TaskStatus.PENDING
    input_data: Dict[str, Any] = Field(default_factory=dict)
    output_data: Optional[Dict[str, Any]] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

class WorkflowRun(BaseModel):
    run_id: str
    user_id: str = "default_user"
    goal: str
    status: str = TaskStatus.PENDING
    tasks: List[Task] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class IntentSchema(BaseModel):
    action: str = Field(description="The core action the user wants to perform")
    target: str = Field(description="The target of the action")
    context: Optional[str] = Field(None, description="Any additional context provided")

class PlanStepSchema(BaseModel):
    step_name: str = Field(description="The name of the step")
    tool_name: Optional[str] = Field(None, description="The tool to execute, if any")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Arguments for the tool")

class PlanSchema(BaseModel):
    steps: List[PlanStepSchema] = Field(description="The list of steps to execute the intent")
