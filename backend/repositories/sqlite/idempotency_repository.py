"""
AgentOS — SQLite Idempotency Repository

Exactly-once execution ledger using atomic INSERT with unique constraint.
Prevents duplicate tool calls in concurrent/distributed environments.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from backend.repositories.base import BaseIdempotencyRepository
from backend.repositories.sqlite.database import DatabaseManager

logger = logging.getLogger(__name__)


class SQLiteIdempotencyRepository(BaseIdempotencyRepository):

    def __init__(self, db: DatabaseManager):
        self.db = db

    async def atomic_insert(self, key: str, workflow_id: str, task_id: str) -> bool:
        """
        Attempts atomic INSERT. Returns True if we own the lock.
        Uses INSERT ... ON CONFLICT DO NOTHING + rowcount check.
        
        This is the core idempotency mechanism:
        - If INSERT succeeds (rowcount=1): we claimed the execution lock
        - If INSERT is ignored (rowcount=0): another worker already has it
        """
        now = datetime.now(timezone.utc).isoformat()
        conn = await self.db.connection()

        cursor = await conn.execute(
            """
            INSERT INTO idempotency_ledger (idempotency_key, workflow_id, task_id, status, created_at, updated_at)
            VALUES (?, ?, ?, 'running', ?, ?)
            ON CONFLICT(idempotency_key) DO NOTHING
            """,
            (key, workflow_id, task_id, now, now),
        )
        await conn.commit()

        success = cursor.rowcount > 0
        if success:
            logger.debug(f"[IDEMPOTENCY] Claimed execution lock: {key[:16]}...")
        else:
            logger.debug(f"[IDEMPOTENCY] Key already exists: {key[:16]}...")
        return success

    async def get_record(self, key: str) -> Optional[Dict[str, Any]]:
        row = await self.db.fetch_one(
            "SELECT * FROM idempotency_ledger WHERE idempotency_key = ?",
            (key,),
        )
        return dict(row) if row else None

    async def commit_success(self, key: str, result_payload: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        await self.db.execute(
            """
            UPDATE idempotency_ledger
            SET status = 'completed', result_payload = ?, updated_at = ?
            WHERE idempotency_key = ?
            """,
            (result_payload, now, key),
        )
        await self.db.commit()
        logger.debug(f"[IDEMPOTENCY] Committed success: {key[:16]}...")

    async def commit_failure(self, key: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        await self.db.execute(
            """
            UPDATE idempotency_ledger
            SET status = 'failed', updated_at = ?
            WHERE idempotency_key = ?
            """,
            (now, key),
        )
        await self.db.commit()
        logger.debug(f"[IDEMPOTENCY] Committed failure: {key[:16]}...")
