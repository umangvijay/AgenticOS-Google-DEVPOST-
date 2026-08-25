"""
AgentOS — SQLite Notification Repository

In-app notification persistence for the Notification Action Center.
"""

import json
import uuid
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from backend.repositories.base import BaseNotificationRepository
from backend.repositories.sqlite.database import DatabaseManager

logger = logging.getLogger(__name__)


class SQLiteNotificationRepository(BaseNotificationRepository):

    def __init__(self, db: DatabaseManager):
        self.db = db

    async def create_notification(self, notification_data: Dict[str, Any]) -> str:
        n = notification_data
        notification_id = n.get("id", str(uuid.uuid4()))
        now = datetime.now(timezone.utc).isoformat()

        await self.db.execute(
            """
            INSERT INTO notifications (id, user_id, type, title, body, metadata, is_read, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                notification_id,
                n["user_id"],
                n["type"],
                n["title"],
                n.get("body", ""),
                json.dumps(n.get("metadata", {})),
                0,
                n.get("created_at", now),
            ),
        )
        await self.db.commit()
        return notification_id

    async def list_notifications(
        self, user_id: str, unread_only: bool = False, limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        if unread_only:
            rows = await self.db.fetch_all(
                """
                SELECT * FROM notifications
                WHERE user_id = ? AND is_read = 0
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                (user_id, limit, offset),
            )
        else:
            rows = await self.db.fetch_all(
                """
                SELECT * FROM notifications
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                (user_id, limit, offset),
            )

        return [self._row_to_dict(r) for r in rows]

    async def mark_read(self, notification_id: str) -> None:
        await self.db.execute(
            "UPDATE notifications SET is_read = 1 WHERE id = ?",
            (notification_id,),
        )
        await self.db.commit()

    async def mark_all_read(self, user_id: str) -> int:
        conn = await self.db.connection()
        cursor = await conn.execute(
            "UPDATE notifications SET is_read = 1 WHERE user_id = ? AND is_read = 0",
            (user_id,),
        )
        await conn.commit()
        return cursor.rowcount

    async def get_unread_count(self, user_id: str) -> int:
        row = await self.db.fetch_one(
            "SELECT COUNT(*) as cnt FROM notifications WHERE user_id = ? AND is_read = 0",
            (user_id,),
        )
        return row["cnt"] if row else 0

    @staticmethod
    def _row_to_dict(row: dict) -> Dict[str, Any]:
        result = dict(row)
        result["metadata"] = json.loads(result.get("metadata", "{}"))
        result["is_read"] = bool(result.get("is_read", 0))
        return result
