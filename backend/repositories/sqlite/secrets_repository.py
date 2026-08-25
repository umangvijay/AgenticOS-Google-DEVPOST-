"""
AgentOS — SQLite Secrets Repository

Stores/retrieves encrypted ciphertext only.
Encryption/decryption is handled by the SecretsVault service layer.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from backend.repositories.base import BaseSecretsRepository
from backend.repositories.sqlite.database import DatabaseManager

logger = logging.getLogger(__name__)


class SQLiteSecretsRepository(BaseSecretsRepository):

    def __init__(self, db: DatabaseManager):
        self.db = db

    async def store_secret(self, user_id: str, key: str, encrypted_value: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        await self.db.execute(
            """
            INSERT INTO secrets (user_id, key, encrypted_value, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id, key) DO UPDATE SET
                encrypted_value = excluded.encrypted_value,
                updated_at = excluded.updated_at
            """,
            (user_id, key, encrypted_value, now, now),
        )
        await self.db.commit()

    async def get_secret(self, user_id: str, key: str) -> Optional[str]:
        row = await self.db.fetch_one(
            "SELECT encrypted_value FROM secrets WHERE user_id = ? AND key = ?",
            (user_id, key),
        )
        return row["encrypted_value"] if row else None

    async def delete_secret(self, user_id: str, key: str) -> bool:
        conn = await self.db.connection()
        cursor = await conn.execute(
            "DELETE FROM secrets WHERE user_id = ? AND key = ?",
            (user_id, key),
        )
        await conn.commit()
        return cursor.rowcount > 0

    async def list_secret_keys(self, user_id: str) -> List[str]:
        rows = await self.db.fetch_all(
            "SELECT key FROM secrets WHERE user_id = ? ORDER BY key",
            (user_id,),
        )
        return [row["key"] for row in rows]
