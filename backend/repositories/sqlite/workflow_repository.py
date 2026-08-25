"""
AgentOS — SQLite Workflow Repository

Full CRUD matching the existing WorkflowRepository interface.
Atomic task claiming via SQLite transaction (not get-then-write).
SSE event streaming via polling with last_event_id cursor.
"""

import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta

from backend.repositories.base import BaseWorkflowRepository
from backend.repositories.sqlite.database import DatabaseManager

logger = logging.getLogger(__name__)


class SQLiteWorkflowRepository(BaseWorkflowRepository):

    def __init__(self, db: DatabaseManager):
        self.db = db

    # ── Workflow Runs ─────────────────────────────────────────────

    async def save_run(self, run_data: Dict[str, Any]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        conn = await self.db.connection()

        # Upsert the run
        await conn.execute(
            """
            INSERT INTO workflow_runs (run_id, workflow_id, user_id, goal, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                status = excluded.status,
                updated_at = excluded.updated_at
            """,
            (
                run_data["run_id"],
                run_data.get("workflow_id", "default_workflow"),
                run_data.get("user_id", "default_user"),
                run_data["goal"],
                run_data.get("status", "PENDING"),
                run_data.get("created_at", now),
                now,
            ),
        )

        # Upsert all tasks
        tasks = run_data.get("tasks", [])
        for task in tasks:
            await self._upsert_task(conn, run_data["run_id"], task)

        await conn.commit()

    async def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        run_row = await self.db.fetch_one(
            "SELECT * FROM workflow_runs WHERE run_id = ?", (run_id,)
        )
        if not run_row:
            return None

        task_rows = await self.db.fetch_all(
            "SELECT * FROM tasks WHERE run_id = ? ORDER BY rowid", (run_id,)
        )

        result = dict(run_row)
        result["tasks"] = [self._task_row_to_dict(t) for t in task_rows]
        return result

    async def list_runs(self, user_id: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        rows = await self.db.fetch_all(
            """
            SELECT * FROM workflow_runs
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            (user_id, limit, offset),
        )
        runs = []
        for row in rows:
            run = dict(row)
            task_rows = await self.db.fetch_all(
                "SELECT * FROM tasks WHERE run_id = ? ORDER BY rowid",
                (run["run_id"],),
            )
            run["tasks"] = [self._task_row_to_dict(t) for t in task_rows]
            runs.append(run)
        return runs

    async def update_run_status(self, run_id: str, status: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        await self.db.execute(
            "UPDATE workflow_runs SET status = ?, updated_at = ? WHERE run_id = ?",
            (status, now, run_id),
        )
        await self.db.commit()

    async def create_if_absent(self, run_data: Dict[str, Any]) -> bool:
        """Idempotent creation. Returns True if created, False if already exists."""
        now = datetime.now(timezone.utc).isoformat()
        conn = await self.db.connection()
        cursor = await conn.execute(
            """
            INSERT OR IGNORE INTO workflow_runs
                (run_id, workflow_id, user_id, goal, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_data["run_id"],
                run_data.get("workflow_id", "default_workflow"),
                run_data.get("user_id", "default_user"),
                run_data["goal"],
                run_data.get("status", "PENDING"),
                run_data.get("created_at", now),
                now,
            ),
        )
        await conn.commit()
        return cursor.rowcount > 0

    # ── Tasks ─────────────────────────────────────────────────────

    async def save_task(self, task_data: Dict[str, Any]) -> None:
        conn = await self.db.connection()
        await self._upsert_task(conn, task_data["run_id"], task_data)
        await conn.commit()

    async def get_task(self, run_id: str, task_id: str) -> Optional[Dict[str, Any]]:
        row = await self.db.fetch_one(
            "SELECT * FROM tasks WHERE run_id = ? AND task_id = ?",
            (run_id, task_id),
        )
        return self._task_row_to_dict(row) if row else None

    async def update_task(self, run_id: str, task_id: str, updates: Dict[str, Any]) -> None:
        if not updates:
            return

        set_clauses = []
        values = []
        for key, value in updates.items():
            set_clauses.append(f"{key} = ?")
            if isinstance(value, (dict, list)):
                values.append(json.dumps(value))
            elif isinstance(value, bool):
                values.append(1 if value else 0)
            else:
                values.append(value)

        values.extend([run_id, task_id])

        conn = await self.db.connection()
        await conn.execute(
            f"UPDATE tasks SET {', '.join(set_clauses)} WHERE run_id = ? AND task_id = ?",
            tuple(values),
        )
        await conn.commit()

    async def claim_task(self, run_id: str, task_id: str, lease_seconds: int) -> bool:
        """
        Atomic task claiming using a single conditional UPDATE.
        This is a compare-and-swap: only succeeds if the task is in a claimable state.
        No SELECT-then-UPDATE race condition.
        """
        now = datetime.now(timezone.utc)
        lease_expires = now + timedelta(seconds=lease_seconds)

        conn = await self.db.connection()
        cursor = await conn.execute(
            """
            UPDATE tasks
            SET status = 'RUNNING',
                lease_started_at = ?,
                lease_expires_at = ?,
                attempt = attempt + 1
            WHERE run_id = ? AND task_id = ?
              AND (
                status = 'PENDING'
                OR status = 'RETRYING'
                OR (status = 'RUNNING' AND lease_expires_at < ?)
              )
            """,
            (
                now.isoformat(),
                lease_expires.isoformat(),
                run_id,
                task_id,
                now.isoformat(),
            ),
        )
        await conn.commit()

        claimed = cursor.rowcount > 0
        if claimed:
            logger.debug(f"Task {task_id} claimed for run {run_id}")
        return claimed

    # ── Approvals ─────────────────────────────────────────────────

    async def save_approval(self, approval_data: Dict[str, Any]) -> None:
        a = approval_data
        await self.db.execute(
            """
            INSERT INTO approvals (
                approval_id, user_id, tool_name, tool_version, risk_level,
                autonomy_level, arguments, arguments_hash, workflow_id,
                run_id, task_id, requested_at, expires_at, requested_by, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                a["approval_id"], a["user_id"], a["tool_name"], a["tool_version"],
                a["risk_level"], a["autonomy_level"],
                json.dumps(a.get("arguments", {})), a["arguments_hash"],
                a["workflow_id"], a["run_id"], a["task_id"],
                a["requested_at"], a["expires_at"],
                a.get("requested_by", "system"),
                a.get("status", "PENDING"),
            ),
        )
        await self.db.commit()

    async def get_approval(self, approval_id: str) -> Optional[Dict[str, Any]]:
        row = await self.db.fetch_one(
            "SELECT * FROM approvals WHERE approval_id = ?", (approval_id,)
        )
        if not row:
            return None
        result = dict(row)
        result["arguments"] = json.loads(result.get("arguments", "{}"))
        return result

    async def list_pending_approvals(self, user_id: str) -> List[Dict[str, Any]]:
        rows = await self.db.fetch_all(
            "SELECT * FROM approvals WHERE user_id = ? AND status = 'PENDING' ORDER BY requested_at DESC",
            (user_id,),
        )
        results = []
        for row in rows:
            r = dict(row)
            r["arguments"] = json.loads(r.get("arguments", "{}"))
            results.append(r)
        return results

    async def resolve_approval(self, approval_id: str, new_status: str, decision_by: str) -> bool:
        """Atomic compare-and-set: only transitions from PENDING."""
        now = datetime.now(timezone.utc).isoformat()
        conn = await self.db.connection()
        cursor = await conn.execute(
            """
            UPDATE approvals
            SET status = ?, decision_by = ?, decision_at = ?
            WHERE approval_id = ? AND status = 'PENDING'
            """,
            (new_status, decision_by, now, approval_id),
        )
        await conn.commit()
        return cursor.rowcount > 0

    # ── Events (SSE Timeline) ─────────────────────────────────────

    async def save_event(self, event_data: Dict[str, Any]) -> None:
        await self.db.execute(
            """
            INSERT INTO events (
                event_id, timestamp, type, workflow_id, run_id,
                task_id, status, summary, sanitized_metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_data["event_id"],
                event_data["timestamp"],
                event_data["type"],
                event_data["workflow_id"],
                event_data["run_id"],
                event_data.get("task_id"),
                event_data.get("status"),
                event_data["summary"],
                json.dumps(event_data.get("sanitized_metadata", {})),
            ),
        )
        await self.db.commit()

    async def get_events(self, run_id: str, after_event_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        SSE reconnection support: get events after a specific event_id.
        SQLite has no LISTEN/NOTIFY, so SSE uses polling with this cursor.
        """
        if after_event_id:
            # Get the rowid of the cursor event
            cursor_row = await self.db.fetch_one(
                "SELECT rowid FROM events WHERE event_id = ?", (after_event_id,)
            )
            if cursor_row:
                rows = await self.db.fetch_all(
                    """
                    SELECT * FROM events
                    WHERE run_id = ? AND rowid > ?
                    ORDER BY rowid ASC
                    """,
                    (run_id, cursor_row["rowid"]),
                )
            else:
                rows = await self.db.fetch_all(
                    "SELECT * FROM events WHERE run_id = ? ORDER BY rowid ASC",
                    (run_id,),
                )
        else:
            rows = await self.db.fetch_all(
                "SELECT * FROM events WHERE run_id = ? ORDER BY rowid ASC",
                (run_id,),
            )

        results = []
        for row in rows:
            r = dict(row)
            r["sanitized_metadata"] = json.loads(r.get("sanitized_metadata", "{}"))
            results.append(r)
        return results

    # ── Private Helpers ───────────────────────────────────────────

    async def _upsert_task(self, conn, run_id: str, task: Dict[str, Any]) -> None:
        """Insert or update a task."""
        await conn.execute(
            """
            INSERT INTO tasks (
                task_id, run_id, workflow_id, user_id, agent, tool, status,
                input_data, output_data, dependencies, started_at, completed_at,
                lease_started_at, lease_expires_at, attempt, timeout_seconds,
                max_retries, recovery_enabled, max_recoveries, max_total_attempts,
                recovery_attempts, original_input, recovery_history,
                error, error_type, trace_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id, task_id) DO UPDATE SET
                status = excluded.status,
                input_data = excluded.input_data,
                output_data = excluded.output_data,
                started_at = excluded.started_at,
                completed_at = excluded.completed_at,
                lease_started_at = excluded.lease_started_at,
                lease_expires_at = excluded.lease_expires_at,
                attempt = excluded.attempt,
                recovery_attempts = excluded.recovery_attempts,
                recovery_history = excluded.recovery_history,
                error = excluded.error,
                error_type = excluded.error_type,
                trace_id = excluded.trace_id
            """,
            (
                task["task_id"],
                run_id,
                task.get("workflow_id", "default_workflow"),
                task.get("user_id", "default_user"),
                task["agent"],
                task.get("tool"),
                task.get("status", "PENDING"),
                json.dumps(task.get("input_data", {})),
                json.dumps(task.get("output_data")) if task.get("output_data") else None,
                json.dumps(task.get("dependencies", [])),
                task.get("started_at"),
                task.get("completed_at"),
                task.get("lease_started_at"),
                task.get("lease_expires_at"),
                task.get("attempt", 0),
                task.get("timeout_seconds", 60),
                task.get("max_retries", 3),
                1 if task.get("recovery_enabled", False) else 0,
                task.get("max_recoveries", 3),
                task.get("max_total_attempts", 5),
                task.get("recovery_attempts", 0),
                json.dumps(task.get("original_input")) if task.get("original_input") else None,
                json.dumps(task.get("recovery_history", [])),
                task.get("error"),
                task.get("error_type"),
                task.get("trace_id"),
            ),
        )

    @staticmethod
    def _task_row_to_dict(row: dict) -> Optional[Dict[str, Any]]:
        """Convert a task row to a dict, deserializing JSON fields."""
        if not row:
            return None
        result = dict(row)
        result["input_data"] = json.loads(result.get("input_data", "{}"))
        result["output_data"] = json.loads(result["output_data"]) if result.get("output_data") else None
        result["dependencies"] = json.loads(result.get("dependencies", "[]"))
        result["recovery_history"] = json.loads(result.get("recovery_history", "[]"))
        result["original_input"] = json.loads(result["original_input"]) if result.get("original_input") else None
        result["recovery_enabled"] = bool(result.get("recovery_enabled", 0))
        return result
