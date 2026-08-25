"""
AgentOS — Notifications Router

GET  /api/v1/notifications           — List notifications
GET  /api/v1/notifications/unread    — Get unread count
POST /api/v1/notifications/{id}/read — Mark as read
POST /api/v1/notifications/read-all  — Mark all as read
GET  /api/v1/notifications/stream    — SSE real-time notifications
"""

import json
import asyncio
import logging

from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import StreamingResponse

from backend.api.dependencies.auth import get_current_user, AuthenticatedUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _get_factory(request: Request):
    factory = getattr(request.app.state, "factory", None)
    if not factory:
        raise HTTPException(status_code=500, detail="Server not initialized")
    return factory


@router.get("")
async def list_notifications(
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    unread_only: bool = False,
    limit: int = 50,
    offset: int = 0,
):
    """List notifications for the current user."""
    factory = _get_factory(request)
    notifications = await factory.notification_repo.list_notifications(
        user.user_id, unread_only=unread_only, limit=limit, offset=offset
    )
    unread_count = await factory.notification_repo.get_unread_count(user.user_id)
    return {
        "notifications": notifications,
        "count": len(notifications),
        "unread_count": unread_count,
    }


@router.get("/unread")
async def get_unread_count(
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Get unread notification count — lightweight poll endpoint."""
    factory = _get_factory(request)
    count = await factory.notification_repo.get_unread_count(user.user_id)
    return {"unread_count": count}


@router.post("/{notification_id}/read")
async def mark_read(
    notification_id: str,
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Mark a single notification as read."""
    factory = _get_factory(request)
    await factory.notification_repo.mark_read(notification_id)
    return {"notification_id": notification_id, "is_read": True}


@router.post("/read-all")
async def mark_all_read(
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Mark all notifications as read for the current user."""
    factory = _get_factory(request)
    count = await factory.notification_repo.mark_all_read(user.user_id)
    return {"marked_read": count}


@router.get("/stream")
async def stream_notifications(
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """
    SSE stream for real-time notifications.
    Frontend connects on login and receives push updates.
    """
    factory = _get_factory(request)

    async def notification_generator():
        """Poll for new notifications every 3 seconds."""
        last_count = 0
        while True:
            if await request.is_disconnected():
                break

            current_count = await factory.notification_repo.get_unread_count(user.user_id)

            if current_count != last_count:
                # New notification(s) — send latest
                notifications = await factory.notification_repo.list_notifications(
                    user.user_id, unread_only=True, limit=5
                )
                payload = {
                    "unread_count": current_count,
                    "latest": notifications[:3],
                }
                yield f"event: notification\ndata: {json.dumps(payload)}\n\n"
                last_count = current_count
            else:
                # Heartbeat to keep connection alive
                yield f"event: heartbeat\ndata: {{}}\n\n"

            await asyncio.sleep(3)

    return StreamingResponse(
        notification_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
