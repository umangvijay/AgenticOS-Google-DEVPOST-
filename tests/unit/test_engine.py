import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from backend.models.schemas import WorkflowRun, Task, TaskStatus, TaskTriggerEvent, ErrorType
from backend.repositories.workflow_repository import InMemoryWorkflowRepository
from backend.repositories.in_memory_message_bus import InMemoryMessageBus, InMemoryMessageContext
from backend.engine.engine import WorkflowEngine

@pytest.fixture
def engine():
    repo = InMemoryWorkflowRepository()
    bus = InMemoryMessageBus()
    return WorkflowEngine(repo, bus)

def test_idempotency_claim(engine):
    run_id = "run_1"
    run = WorkflowRun(run_id=run_id, goal="test")
    task = Task(task_id="T1", workflow_id="wf", run_id=run_id, agent="IntentAgent")
    run.tasks.append(task)
    engine.repo.save_run(run)
    
    # First claim should succeed
    assert engine.repo.claim_task(run_id, "T1", lease_seconds=60) == True
    # Second claim should fail because it's now RUNNING
    assert engine.repo.claim_task(run_id, "T1", lease_seconds=60) == False

@pytest.mark.asyncio
async def test_evaluate_dag_triggering(engine):
    run_id = "run_1"
    run = WorkflowRun(run_id=run_id, goal="test")
    # A has no deps, B depends on A
    t1 = Task(task_id="A", workflow_id="wf", run_id=run_id, agent="IntentAgent", dependencies=[])
    t2 = Task(task_id="B", workflow_id="wf", run_id=run_id, agent="PlannerAgent", dependencies=["A"])
    run.tasks.extend([t1, t2])
    engine.repo.save_run(run)
    
    # Eval DAG should trigger A only
    await engine.evaluate_dag(run_id)
    
    # A should be PENDING (triggered), B should be WAITING
    assert engine.repo.get_run(run_id).tasks[0].status == TaskStatus.PENDING
    assert engine.repo.get_run(run_id).tasks[1].status == TaskStatus.WAITING
    
    # Simulate A completing
    t1.status = TaskStatus.COMPLETED
    engine.repo.update_task(run_id, t1)
    
    # Eval DAG should now trigger B
    await engine.evaluate_dag(run_id)
    assert engine.repo.get_run(run_id).tasks[1].status == TaskStatus.PENDING

@pytest.mark.asyncio
async def test_failed_task_blocks_downstream(engine):
    run_id = "run_1"
    run = WorkflowRun(run_id=run_id, goal="test")
    t1 = Task(task_id="A", workflow_id="wf", run_id=run_id, agent="IntentAgent", status=TaskStatus.FAILED)
    t2 = Task(task_id="B", workflow_id="wf", run_id=run_id, agent="PlannerAgent", dependencies=["A"])
    run.tasks.extend([t1, t2])
    engine.repo.save_run(run)
    
    await engine.evaluate_dag(run_id)
    
    assert engine.repo.get_run(run_id).tasks[1].status == TaskStatus.BLOCKED
    assert engine.repo.get_run(run_id).status == TaskStatus.FAILED

@pytest.mark.asyncio
async def test_execute_task_timeout(engine):
    run_id = "run_1"
    run = WorkflowRun(run_id=run_id, goal="test")
    t1 = Task(task_id="A", workflow_id="wf", run_id=run_id, agent="IntentAgent", timeout_seconds=1)
    run.tasks.append(t1)
    engine.repo.save_run(run)
    
    async def slow_mock(*args, **kwargs):
        await asyncio.sleep(2)
        return []
        
    with patch("backend.engine.engine.InMemoryRunner.run_debug", new_callable=AsyncMock) as mock_run:
        mock_run.side_effect = slow_mock
        await engine.execute_task(run_id, "A")
        
    updated_task = engine.repo.get_run(run_id).tasks[0]
    assert updated_task.status == TaskStatus.RETRYING
    assert updated_task.error_type == ErrorType.TIMEOUT_ERROR

@pytest.mark.asyncio
async def test_cancellation(engine):
    run_id = "run_1"
    run = WorkflowRun(run_id=run_id, goal="test", status=TaskStatus.CANCELLED)
    t1 = Task(task_id="A", workflow_id="wf", run_id=run_id, agent="IntentAgent")
    run.tasks.append(t1)
    engine.repo.save_run(run)
    
    await engine.execute_task(run_id, "A")
    updated_task = engine.repo.get_run(run_id).tasks[0]
    assert updated_task.status == TaskStatus.CANCELLED

@pytest.mark.asyncio
async def test_checkpoint_resume_no_recompute(engine):
    run_id = "run_1"
    run = WorkflowRun(run_id=run_id, goal="test")
    t1 = Task(task_id="A", workflow_id="wf", run_id=run_id, agent="IntentAgent", status=TaskStatus.COMPLETED)
    t2 = Task(task_id="B", workflow_id="wf", run_id=run_id, agent="PlannerAgent", dependencies=["A"], status=TaskStatus.RUNNING, lease_expires_at=None) # Assume worker crashed and left it
    run.tasks.extend([t1, t2])
    engine.repo.save_run(run)
    
    # We forcefully reset stale tasks to simulate resume
    # Here we simulate evaluate_dag catching up
    # Wait, claim_task handles stale lease recovery. Let's make it stale.
    from datetime import datetime, timedelta, timezone
    t2.lease_expires_at = datetime.now(timezone.utc) - timedelta(minutes=5)
    engine.repo.update_task(run_id, t2)
    
    # Execute B should succeed in claiming because it's stale
    with patch("backend.engine.engine.InMemoryRunner.run_debug", new_callable=AsyncMock) as mock_run:
        class MockEvent:
            def __init__(self):
                self.output = "mock"
        mock_run.return_value = [MockEvent()]
        
        await engine.execute_task(run_id, "B")
        
    updated_run = engine.repo.get_run(run_id)
    assert updated_run.tasks[1].status == TaskStatus.COMPLETED
    # A should still be completed and untouched
    assert updated_run.tasks[0].status == TaskStatus.COMPLETED
