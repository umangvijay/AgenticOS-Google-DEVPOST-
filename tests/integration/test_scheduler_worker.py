import pytest
import asyncio
from datetime import datetime, timezone
from backend.models.schedule import Schedule, SchedulerTriggerEvent
from backend.repositories.schedule_repository import InMemoryScheduleRepository
from backend.repositories.workflow_repository import InMemoryWorkflowRepository
from backend.repositories.in_memory_message_bus import InMemoryMessageBus
from backend.engine.engine import WorkflowEngine
from backend.worker import start_worker
from backend.models.schemas import TaskStatus

@pytest.mark.asyncio
async def test_worker_idempotent_schedule_trigger():
    msg_bus = InMemoryMessageBus()
    workflow_repo = InMemoryWorkflowRepository()
    engine = WorkflowEngine(workflow_repo, msg_bus)
    schedule_repo = InMemoryScheduleRepository()
    
    # Start worker in background
    worker_task = asyncio.create_task(start_worker(msg_bus, engine, schedule_repo))
    
    # Create Schedule
    sch = Schedule(
        schedule_id="sch_e2e_1",
        name="Test Idempotency",
        cron_expression="*/5 * * * *",
        goal="Do scheduled task"
    )
    schedule_repo.create_schedule(sch)
    
    # Logical scheduled time
    dt = datetime(2026, 8, 23, 10, 0, 0, tzinfo=timezone.utc)
    
    # Send first trigger
    event_payload = {
        "schedule_id": "sch_e2e_1",
        "scheduled_time": dt.isoformat()
    }
    
    await msg_bus.publish("agentos-scheduler-triggers", event_payload)
    
    # Yield to let worker process
    await asyncio.sleep(0.1)
    
    # Verify run was created
    runs = list(workflow_repo._store.values())
    assert len(runs) == 1
    run1 = runs[0]
    assert run1.goal == "Do scheduled task"
    assert run1.status == TaskStatus.PENDING
    assert run1.run_id.startswith("sch-")
    
    # Send DUPLICATE trigger for the same logical time
    await msg_bus.publish("agentos-scheduler-triggers", event_payload)
    
    # Yield to let worker process
    await asyncio.sleep(0.1)
    
    # Verify NO new run was created
    runs_after = list(workflow_repo._store.values())
    assert len(runs_after) == 1
    assert runs_after[0].run_id == run1.run_id
    
    # Send trigger for a DIFFERENT logical time
    dt2 = datetime(2026, 8, 23, 10, 5, 0, tzinfo=timezone.utc)
    event_payload2 = {
        "schedule_id": "sch_e2e_1",
        "scheduled_time": dt2.isoformat()
    }
    await msg_bus.publish("agentos-scheduler-triggers", event_payload2)
    
    await asyncio.sleep(0.1)
    
    # Verify NEW run was created
    runs_final = list(workflow_repo._store.values())
    assert len(runs_final) == 2
    
    worker_task.cancel()
