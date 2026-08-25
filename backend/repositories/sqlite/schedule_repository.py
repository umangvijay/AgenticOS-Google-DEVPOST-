"""
AgentOS — SQLite Schedule Repository

Schedule CRUD with execution history tracking and idempotent trigger detection.
"""

import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from backend.repositories.base import BaseScheduleRepository
from backend.repositories.sqlite.database import DatabaseManager

logger = logging.getLogger(__name__)


class SQLiteScheduleRepository(BaseScheduleRepository):

    def __init__(self, db: DatabaseManager):
        self.db = db

    async def create_schedule(self, schedule_data: Dict[str, Any]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        s = schedule_data
        await self.db.execute(
            """
            INSERT INTO schedules (
                schedule_id, user_id, name, goal, cron_expression, schedule_type,
                timezone, status, next_run_at, last_run_at, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                s["schedule_id"], s["user_id"], s["name"], s["goal"],
                s.get("cron_expression"), s.get("schedule_type", "one_time"),
                s.get("timezone", "UTC"), s.get("status", "active"),
                s.get("next_run_at"), s.get("last_run_at"),
                s.get("created_at", now), now,
            ),
        )
        await self.db.commit()

    async def get_schedule(self, schedule_id: str) -> Optional[Dict[str, Any]]:
        row = await self.db.fetch_one(
            "SELECT * FROM schedules WHERE schedule_id = ?", (schedule_id,)
        )
        return dict(row) if row else None

    async def list_schedules(self, user_id: str) -> List[Dict[str, Any]]:
        rows = await self.db.fetch_all(
            "SELECT * FROM schedules WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        )
        return [dict(r) for r in rows]

    async def update_schedule(self, schedule_id: str, updates: Dict[str, Any]) -> None:
        if not updates:
            return
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()

        set_clauses = []
        values = []
        for key, value in updates.items():
            set_clauses.append(f"{key} = ?")
            values.append(value)
        values.append(schedule_id)

        conn = await self.db.connection()
        await conn.execute(
            f"UPDATE schedules SET {', '.join(set_clauses)} WHERE schedule_id = ?",
            tuple(values),
        )
        await conn.commit()

    async def delete_schedule(self, schedule_id: str) -> bool:
        conn = await self.db.connection()
        cursor = await conn.execute(
            "DELETE FROM schedules WHERE schedule_id = ?", (schedule_id,)
        )
        await conn.commit()
        return cursor.rowcount > 0

    async def record_execution(self, schedule_id: str, run_id: str, status: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        conn = await self.db.connection()
        await conn.execute(
            """
            INSERT INTO schedule_executions (schedule_id, run_id, status, triggered_at)
            VALUES (?, ?, ?, ?)
            """,
            (schedule_id, run_id, status, now),
        )
        # Update schedule's last_run_at
        await conn.execute(
            "UPDATE schedules SET last_run_at = ?, updated_at = ? WHERE schedule_id = ?",
            (now, now, schedule_id),
        )
        await conn.commit()

    async def get_execution_history(self, schedule_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        rows = await self.db.fetch_all(
            """
            SELECT * FROM schedule_executions
            WHERE schedule_id = ?
            ORDER BY triggered_at DESC
            LIMIT ?
            """,
            (schedule_id, limit),
        )
        return [dict(r) for r in rows]
