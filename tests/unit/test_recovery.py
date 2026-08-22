import pytest
import asyncio
from datetime import datetime, timezone
from backend.models.schemas import Task, TaskStatus, ErrorType, SemanticErrorReason, WorkflowRun
from backend.models.recovery import RecoveryAction, RecoveryActionEnum, RecoveryContext
from backend.engine.engine import WorkflowEngine
from backend.repositories.message_bus import MessageBus

class InMemoryMessageBus(MessageBus):
    def __init__(self):
        self.published_messages = []
        
    async def publish(self, topic: str, message: Any) -> None:
        self.published_messages.append((topic, message))
        
    async def consume(self, topic: str, handler: Any) -> None:
        pass

@pytest.mark.asyncio
async def test_semantic_error_triggers_recovery():
    repo = InMemoryWorkflowRepository()
    bus = InMemoryMessageBus()
    engine = WorkflowEngine(workflow_repo=repo, message_bus=bus)
    
    run = WorkflowRun(run_id="r1", goal="test")
    task = Task(
        task_id="t1", 
        workflow_id="w1", 
        run_id="r1", 
        agent="a",
        recovery_enabled=True,
        max_recoveries=3,
        input_data={"bad_field": 123}
    )
    run.tasks.append(task)
    repo.save_run(run)
    
    # Simulate a SemanticException being caught in execute_task
    # We call _handle_task_failure directly for testing
    engine._handle_task_failure(
        run_id="r1", 
        task=task, 
        error_msg="Invalid type for bad_field", 
        error_type=ErrorType.SEMANTIC_ERROR, 
        semantic_reason=SemanticErrorReason.TYPE_MISMATCH
    )
    
    # Check that task status is RECOVERING
    fetched_task = repo.get_run("r1").tasks[0]
    assert fetched_task.status == TaskStatus.RECOVERING
    assert fetched_task.original_input == {"bad_field": 123}
    
    # Check that TaskRecoveryEvent was published
    await asyncio.sleep(0.1) # yield to let async task run
    assert len(bus.published_messages) > 0
    event = bus.published_messages[0][1]
    assert event.task_id == "t1"
    assert event.recovery_attempt == 1

@pytest.mark.asyncio
async def test_max_total_attempts_enforced():
    repo = InMemoryWorkflowRepository()
    bus = InMemoryMessageBus()
    engine = WorkflowEngine(workflow_repo=repo, message_bus=bus)
    
    run = WorkflowRun(run_id="r2", goal="test")
    task = Task(
        task_id="t2", 
        workflow_id="w2", 
        run_id="r2", 
        agent="a",
        attempt=4,
        recovery_attempts=1,
        max_total_attempts=5, # 4+1 = 5
        recovery_enabled=True
    )
    run.tasks.append(task)
    repo.save_run(run)
    
    engine._handle_task_failure(
        run_id="r2", 
        task=task, 
        error_msg="Some error", 
        error_type=ErrorType.SEMANTIC_ERROR
    )
    
    # Task should be FAILED permanently
    fetched_task = repo.get_run("r2").tasks[0]
    assert fetched_task.status == TaskStatus.FAILED

def test_recovery_action_schema():
    # Verify strict structured output expectations
    action = RecoveryAction(
        action=RecoveryActionEnum.REPAIR,
        corrected_input={"good_field": "123"},
        rationale="Fixed type mismatch"
    )
    assert action.action == "REPAIR"
    assert action.corrected_input == {"good_field": "123"}
