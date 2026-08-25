"""
AgentOS — Notification Service

Creates and delivers notifications for workflow events.
Supports SSE push and in-app notification center.

Notification types:
    APPROVAL_REQUIRED  — Workflow paused, needs human decision
    WORKFLOW_COMPLETED — Goal achieved, artifacts ready
    WORKFLOW_FAILED    — Unrecoverable failure
    CIRCUIT_BREAKER    — Upstream integration down
    MCP_CREATED        — New integration auto-generated
    SELF_HEALING       — RecoveryAgent fixed an error
    TOKEN_WARNING      — Approaching daily token limit
    SYSTEM             — System announcements
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from enum import Enum

logger = logging.getLogger(__name__)


class NotificationType(str, Enum):
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    WORKFLOW_COMPLETED = "WORKFLOW_COMPLETED"
    WORKFLOW_FAILED = "WORKFLOW_FAILED"
    CIRCUIT_BREAKER = "CIRCUIT_BREAKER"
    MCP_CREATED = "MCP_CREATED"
    SELF_HEALING = "SELF_HEALING"
    TOKEN_WARNING = "TOKEN_WARNING"
    SYSTEM = "SYSTEM"


class NotificationPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


# Map notification types to priorities
TYPE_PRIORITIES = {
    NotificationType.APPROVAL_REQUIRED: NotificationPriority.URGENT,
    NotificationType.WORKFLOW_COMPLETED: NotificationPriority.MEDIUM,
    NotificationType.WORKFLOW_FAILED: NotificationPriority.HIGH,
    NotificationType.CIRCUIT_BREAKER: NotificationPriority.HIGH,
    NotificationType.MCP_CREATED: NotificationPriority.LOW,
    NotificationType.SELF_HEALING: NotificationPriority.LOW,
    NotificationType.TOKEN_WARNING: NotificationPriority.HIGH,
    NotificationType.SYSTEM: NotificationPriority.MEDIUM,
}


class NotificationService:
    """
    Central notification service.
    
    Usage:
        svc = NotificationService(notification_repo)
        
        await svc.notify_approval_required(user_id, approval_data)
        await svc.notify_workflow_completed(user_id, run_id, goal)
    """

    def __init__(self, notification_repo):
        self.repo = notification_repo

    async def create(
        self,
        user_id: str,
        notification_type: str,
        title: str,
        body: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Create a notification. Returns notification_id."""
        notification_id = await self.repo.create_notification({
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "type": notification_type,
            "title": title,
            "body": body,
            "metadata": metadata or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        logger.info(
            f"[NOTIFY] {notification_type} for user {user_id[:8]}...: {title}"
        )
        return notification_id

    # ── Typed Helpers ─────────────────────────────────────────────

    async def notify_approval_required(
        self,
        user_id: str,
        approval_id: str,
        tool_name: str,
        risk_level: str,
        workflow_id: str,
        run_id: str,
    ) -> str:
        return await self.create(
            user_id=user_id,
            notification_type=NotificationType.APPROVAL_REQUIRED,
            title=f"Approval needed: {tool_name}",
            body=f"A workflow action requires your approval. Risk level: {risk_level}.",
            metadata={
                "approval_id": approval_id,
                "tool_name": tool_name,
                "risk_level": risk_level,
                "workflow_id": workflow_id,
                "run_id": run_id,
            },
        )

    async def notify_workflow_completed(
        self, user_id: str, run_id: str, goal: str
    ) -> str:
        return await self.create(
            user_id=user_id,
            notification_type=NotificationType.WORKFLOW_COMPLETED,
            title="Workflow completed",
            body=f"Your workflow has finished: {goal[:100]}",
            metadata={"run_id": run_id, "goal": goal},
        )

    async def notify_workflow_failed(
        self, user_id: str, run_id: str, goal: str, error: str
    ) -> str:
        return await self.create(
            user_id=user_id,
            notification_type=NotificationType.WORKFLOW_FAILED,
            title="Workflow failed",
            body=f"Workflow could not complete: {error[:200]}",
            metadata={"run_id": run_id, "goal": goal, "error": error},
        )

    async def notify_circuit_breaker(
        self, user_id: str, mcp_id: str, mcp_name: str
    ) -> str:
        return await self.create(
            user_id=user_id,
            notification_type=NotificationType.CIRCUIT_BREAKER,
            title=f"Integration down: {mcp_name}",
            body=f"The {mcp_name} integration is experiencing issues. Affected workflows are paused.",
            metadata={"mcp_id": mcp_id, "mcp_name": mcp_name},
        )

    async def notify_mcp_created(
        self, user_id: str, mcp_id: str, mcp_name: str
    ) -> str:
        return await self.create(
            user_id=user_id,
            notification_type=NotificationType.MCP_CREATED,
            title=f"New integration: {mcp_name}",
            body=f"AgentOS automatically built a new integration for {mcp_name}.",
            metadata={"mcp_id": mcp_id, "mcp_name": mcp_name},
        )

    async def notify_self_healing(
        self, user_id: str, run_id: str, task_id: str, fix_description: str
    ) -> str:
        return await self.create(
            user_id=user_id,
            notification_type=NotificationType.SELF_HEALING,
            title="Auto-recovery successful",
            body=fix_description[:200],
            metadata={"run_id": run_id, "task_id": task_id},
        )

    async def notify_token_warning(
        self, user_id: str, used: int, limit: int
    ) -> str:
        pct = int((used / limit) * 100) if limit > 0 else 100
        return await self.create(
            user_id=user_id,
            notification_type=NotificationType.TOKEN_WARNING,
            title=f"Token usage at {pct}%",
            body=f"You've used {used:,} of your daily {limit:,} token budget.",
            metadata={"used": used, "limit": limit, "percentage": pct},
        )

    # ── Query Helpers ─────────────────────────────────────────────

    async def get_unread_count(self, user_id: str) -> int:
        return await self.repo.get_unread_count(user_id)

    async def list_notifications(
        self, user_id: str, unread_only: bool = False, limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        return await self.repo.list_notifications(user_id, unread_only, limit, offset)

    async def mark_read(self, notification_id: str) -> None:
        await self.repo.mark_read(notification_id)

    async def mark_all_read(self, user_id: str) -> int:
        return await self.repo.mark_all_read(user_id)
