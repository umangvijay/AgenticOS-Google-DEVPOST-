"""
AgentOS — SQLite Refresh Token Repository

Single-use refresh tokens with rotation. Supports logout-everywhere.
"""

import logging
from typing import Optional, List
from datetime import datetime, timezone

from backend.repositories.base import BaseRefreshTokenRepository
from backend.repositories.sqlite.database import DatabaseManager

logger = logging.getLogger(__name__)


class SQLiteRefreshTokenRepository(BaseRefreshTokenRepository):

    def __init__(self, db: DatabaseManager):
        self.db = db

    async def store_token(self, user_id: str, token_hash: str, expires_at: datetime) -> None:
        now = datetime.now(timezone.utc).isoformat()
        await self.db.execute(
            """
            INSERT INTO refresh_tokens (token_hash, user_id, expires_at, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (token_hash, user_id, expires_at.isoformat(), now),
        )
        await self.db.commit()

    async def validate_and_consume(self, token_hash: str) -> Optional[str]:
        """
        Atomically validate and delete a refresh token (single-use).
        Returns user_id if valid, None if not found or expired.
        """
        now = datetime.now(timezone.utc).isoformat()
        conn = await self.db.connection()

        # Fetch the token
        row = await self.db.fetch_one(
            "SELECT user_id, expires_at FROM refresh_tokens WHERE token_hash = ?",
            (token_hash,),
        )
        if not row:
            return None

        # Check expiry
        if row["expires_at"] < now:
            # Expired — clean it up
            await conn.execute(
                "DELETE FROM refresh_tokens WHERE token_hash = ?", (token_hash,)
            )
            await conn.commit()
            return None

        # Delete (consume) the token atomically
        cursor = await conn.execute(
            "DELETE FROM refresh_tokens WHERE token_hash = ?", (token_hash,)
        )
        await conn.commit()

        if cursor.rowcount > 0:
            return row["user_id"]
        return None

    async def revoke_all_for_user(self, user_id: str) -> int:
        conn = await self.db.connection()
        cursor = await conn.execute(
            "DELETE FROM refresh_tokens WHERE user_id = ?", (user_id,)
        )
        await conn.commit()
        return cursor.rowcount

    async def cleanup_expired(self) -> int:
        now = datetime.now(timezone.utc).isoformat()
        conn = await self.db.connection()
        cursor = await conn.execute(
            "DELETE FROM refresh_tokens WHERE expires_at < ?", (now,)
        )
        await conn.commit()
        return cursor.rowcount
