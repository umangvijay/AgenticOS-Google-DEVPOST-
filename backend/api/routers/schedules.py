"""
AgentOS — Schedules Router

POST   /api/v1/schedules              — Create a scheduled workflow
GET    /api/v1/schedules              — List user's schedules
GET    /api/v1/schedules/{id}         — Get schedule detail
PUT    /api/v1/schedules/{id}         — Update schedule
DELETE /api/v1/schedules/{id}         — Delete schedule
POST   /api/v1/schedules/{id}/run     — Run a schedule immediately
POST   /api/v1/schedules/{id}/pause   — Pause/resume a schedule
GET    /api/v1/schedules/{id}/history — Get execution history
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Depends, status
from pydantic import BaseModel

from backend.api.dependencies.auth import get_current_user, AuthenticatedUser, require_not_viewer
from backend.security.input_sanitizer import sanitize_goal, sanitize_text, InputValidationError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/schedules", tags=["schedules"])


def _get_factory(request: Request):
    factory = getattr(request.app.state, "factory", None)
    if not factory:
        raise HTTPException(status_code=500, detail="Server not initialized")
    return factory


class CreateScheduleRequest(BaseModel):
    name: str
    goal: str
    cron_expression: str               # Standard 5-field cron
    timezone: str = "UTC"
    is_enabled: bool = True

class UpdateScheduleRequest(BaseModel):
    name: Optional[str] = None
    goal: Optional[str] = None
    cron_expression: Optional[str] = None
    timezone: Optional[str] = None


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_schedule(
    body: CreateScheduleRequest, request: Request,
    user: AuthenticatedUser = Depends(require_not_viewer),
):
    """Create a new scheduled workflow."""
    factory = _get_factory(request)

    try:
        goal = sanitize_goal(body.goal)
        name = sanitize_text(body.name, "name", max_length=200)
    except InputValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)

    # Validate cron expression
    try:
        from croniter import croniter
        if not croniter.is_valid(body.cron_expression):
            raise ValueError("Invalid")
    except (ValueError, ImportError):
        raise HTTPException(status_code=400, detail=f"Invalid cron expression: {body.cron_expression}")

    schedule_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    # Calculate next run time
    try:
        from croniter import croniter
        cron = croniter(body.cron_expression, datetime.now(timezone.utc))
        next_run = cron.get_next(datetime).isoformat()
    except Exception:
        next_run = None

    schedule = {
        "schedule_id": schedule_id,
        "user_id": user.user_id,
        "name": name,
        "goal": goal,
        "cron_expression": body.cron_expression,
        "timezone": body.timezone,
        "is_enabled": body.is_enabled,
        "next_run_at": next_run,
        "created_at": now,
        "updated_at": now,
    }

    await factory.schedule_repo.create_schedule(schedule)

    await factory.audit_repo.log_event({
        "event_type": "SCHEDULE_CREATED",
        "actor_id": user.user_id, "actor_type": "USER",
        "resource_id": schedule_id,
        "details": {"name": name, "cron": body.cron_expression},
    })

    return schedule


@router.get("")
async def list_schedules(
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """List the user's schedules."""
    factory = _get_factory(request)
    schedules = await factory.schedule_repo.list_schedules(user.user_id)
    return {"schedules": schedules, "count": len(schedules)}


@router.get("/{schedule_id}")
async def get_schedule(
    schedule_id: str, request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Get schedule detail."""
    factory = _get_factory(request)
    schedule = await factory.schedule_repo.get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    if schedule.get("user_id") != user.user_id and not user.is_admin():
        raise HTTPException(status_code=403, detail="Access denied")
    return schedule


@router.put("/{schedule_id}")
async def update_schedule(
    schedule_id: str, body: UpdateScheduleRequest, request: Request,
    user: AuthenticatedUser = Depends(require_not_viewer),
):
    """Update a schedule."""
    factory = _get_factory(request)
    schedule = await factory.schedule_repo.get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    if schedule.get("user_id") != user.user_id and not user.is_admin():
        raise HTTPException(status_code=403, detail="Access denied")

    updates = {}
    if body.name is not None:
        try:
            updates["name"] = sanitize_text(body.name, "name", max_length=200)
        except InputValidationError as e:
            raise HTTPException(status_code=400, detail=e.message)
    if body.goal is not None:
        try:
            updates["goal"] = sanitize_goal(body.goal)
        except InputValidationError as e:
            raise HTTPException(status_code=400, detail=e.message)
    if body.cron_expression is not None:
        try:
            from croniter import croniter
            if not croniter.is_valid(body.cron_expression):
                raise ValueError()
            updates["cron_expression"] = body.cron_expression
        except (ValueError, ImportError):
            raise HTTPException(status_code=400, detail="Invalid cron expression")
    if body.timezone is not None:
        updates["timezone"] = body.timezone

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    await factory.schedule_repo.update_schedule(schedule_id, updates)

    return await factory.schedule_repo.get_schedule(schedule_id)


@router.delete("/{schedule_id}")
async def delete_schedule(
    schedule_id: str, request: Request,
    user: AuthenticatedUser = Depends(require_not_viewer),
):
    """Delete a schedule."""
    factory = _get_factory(request)
    schedule = await factory.schedule_repo.get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    if schedule.get("user_id") != user.user_id and not user.is_admin():
        raise HTTPException(status_code=403, detail="Access denied")

    await factory.schedule_repo.delete_schedule(schedule_id)
    return {"schedule_id": schedule_id, "deleted": True}


@router.post("/{schedule_id}/run")
async def run_now(
    schedule_id: str, request: Request,
    user: AuthenticatedUser = Depends(require_not_viewer),
):
    """Execute a schedule immediately (on-demand run)."""
    factory = _get_factory(request)
    schedule = await factory.schedule_repo.get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    if schedule.get("user_id") != user.user_id and not user.is_admin():
        raise HTTPException(status_code=403, detail="Access denied")

    # Record execution
    await factory.schedule_repo.record_execution(
        schedule_id,
        {"triggered_by": "manual", "triggered_at": datetime.now(timezone.utc).isoformat()},
    )

    # TODO: Trigger workflow engine with schedule's goal
    return {
        "schedule_id": schedule_id,
        "message": "Schedule execution triggered.",
        "goal": schedule.get("goal"),
    }


@router.post("/{schedule_id}/pause")
async def toggle_pause(
    schedule_id: str, request: Request,
    user: AuthenticatedUser = Depends(require_not_viewer),
):
    """Toggle pause/resume for a schedule."""
    factory = _get_factory(request)
    schedule = await factory.schedule_repo.get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    if schedule.get("user_id") != user.user_id and not user.is_admin():
        raise HTTPException(status_code=403, detail="Access denied")

    new_state = not schedule.get("is_enabled", True)
    await factory.schedule_repo.update_schedule(schedule_id, {"is_enabled": new_state})

    return {"schedule_id": schedule_id, "is_enabled": new_state}


@router.get("/{schedule_id}/history")
async def get_history(
    schedule_id: str, request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    limit: int = 20,
):
    """Get execution history for a schedule."""
    factory = _get_factory(request)
    schedule = await factory.schedule_repo.get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    if schedule.get("user_id") != user.user_id and not user.is_admin():
        raise HTTPException(status_code=403, detail="Access denied")

    history = await factory.schedule_repo.get_execution_history(schedule_id, limit)
    return {"executions": history, "count": len(history)}
