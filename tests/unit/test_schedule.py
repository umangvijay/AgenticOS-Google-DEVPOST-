import pytest
from datetime import datetime, timezone
import pydantic
from backend.models.schedule import Schedule, SchedulerTriggerEvent, ScheduleStatus
from backend.repositories.schedule_repository import InMemoryScheduleRepository
import hashlib

def test_schedule_valid_cron():
    schedule = Schedule(
        schedule_id="sch_1",
        name="Test Schedule",
        cron_expression="*/5 * * * *",
        goal="Run a test task"
    )
    assert schedule.cron_expression == "*/5 * * * *"
    assert schedule.timezone == "UTC"

def test_schedule_invalid_cron():
    with pytest.raises(pydantic.ValidationError):
        Schedule(
            schedule_id="sch_1",
            name="Test Schedule",
            cron_expression="invalid cron",
            goal="Run a test task"
        )

def test_schedule_invalid_timezone():
    with pytest.raises(pydantic.ValidationError):
        Schedule(
            schedule_id="sch_1",
            name="Test Schedule",
            cron_expression="*/5 * * * *",
            timezone="Invalid/Timezone",
            goal="Run a test task"
        )

def test_idempotent_hash_logic():
    dt = datetime(2026, 8, 23, 10, 0, 0, tzinfo=timezone.utc)
    event1 = SchedulerTriggerEvent(schedule_id="sch_1", scheduled_time=dt)
    
    # Simulate worker logic
    execution_key1 = f"{event1.schedule_id}|{event1.scheduled_time.isoformat()}"
    run_id1 = "sch-" + hashlib.sha256(execution_key1.encode("utf-8")).hexdigest()
    
    # Event with exact same logical time gives same run_id
    event2 = SchedulerTriggerEvent(schedule_id="sch_1", scheduled_time=dt)
    execution_key2 = f"{event2.schedule_id}|{event2.scheduled_time.isoformat()}"
    run_id2 = "sch-" + hashlib.sha256(execution_key2.encode("utf-8")).hexdigest()
    
    assert run_id1 == run_id2
    
    # Different logical time gives different run_id
    dt2 = datetime(2026, 8, 23, 10, 1, 0, tzinfo=timezone.utc)
    event3 = SchedulerTriggerEvent(schedule_id="sch_1", scheduled_time=dt2)
    execution_key3 = f"{event3.schedule_id}|{event3.scheduled_time.isoformat()}"
    run_id3 = "sch-" + hashlib.sha256(execution_key3.encode("utf-8")).hexdigest()
    
    assert run_id1 != run_id3

def test_schedule_repository_crud():
    repo = InMemoryScheduleRepository()
    sch = Schedule(
        schedule_id="sch_1",
        name="Test Schedule",
        cron_expression="*/5 * * * *",
        goal="Run a test task"
    )
    repo.create_schedule(sch)
    
    # Read
    fetched = repo.get_schedule("sch_1")
    assert fetched is not None
    assert fetched.name == "Test Schedule"
    
    # Update Status
    fetched.status = ScheduleStatus.PAUSED
    repo.update_schedule(fetched)
    
    updated = repo.get_schedule("sch_1")
    assert updated.status == ScheduleStatus.PAUSED
    assert updated.updated_at >= fetched.created_at
    
    # Delete
    repo.delete_schedule("sch_1")
    assert repo.get_schedule("sch_1") is None
