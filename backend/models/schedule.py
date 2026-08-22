from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime, timezone
import croniter
import zoneinfo

class ScheduleStatus(str):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    DELETED = "DELETED"

class Schedule(BaseModel):
    schedule_id: str = Field(description="Unique identifier for the schedule")
    user_id: str = Field(default="default_user", description="User who owns the schedule")
    name: str = Field(description="Human readable name of the schedule")
    cron_expression: str = Field(description="Cron expression")
    timezone: str = Field(default="UTC", description="Timezone (e.g. UTC, America/New_York)")
    goal: str = Field(description="The goal for the workflow run")
    status: str = Field(default=ScheduleStatus.ACTIVE)
    scheduler_job_name: Optional[str] = Field(None, description="Physical Cloud Scheduler job name")
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_triggered_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None

    @field_validator("cron_expression")
    def validate_cron(cls, v):
        if not croniter.croniter.is_valid(v):
            raise ValueError("Invalid cron expression")
        return v

    @field_validator("timezone")
    def validate_timezone(cls, v):
        try:
            zoneinfo.ZoneInfo(v)
        except zoneinfo.ZoneInfoNotFoundError:
            raise ValueError(f"Invalid timezone: {v}")
        return v

class SchedulerTriggerEvent(BaseModel):
    schedule_id: str
    scheduled_time: datetime = Field(description="The logical scheduled time of this event")
