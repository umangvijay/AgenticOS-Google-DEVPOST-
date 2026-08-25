"""
AgentOS — SQLite User Repository

CRUD for users with email uniqueness, OAuth support, and brute-force lockout.
"""

import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from backend.repositories.base import BaseUserRepository
from backend.repositories.sqlite.database import DatabaseManager

logger = logging.getLogger(__name__)


class SQLiteUserRepository(BaseUserRepository):

    def __init__(self, db: DatabaseManager):
        self.db = db

    async def create_user(self, user_data: Dict[str, Any]) -> str:
        """Create a new user. Raises sqlite3.IntegrityError if email exists."""
        now = datetime.now(timezone.utc).isoformat()
        user_id = user_data["id"]

        await self.db.execute(
            """
            INSERT INTO users (
                id, email, name, password_hash, auth_provider, google_id,
                avatar_url, role, is_active, failed_login_attempts,
                locked_until, last_login, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                user_data["email"],
                user_data.get("name", ""),
                user_data.get("password_hash"),       # None for OAuth users
                user_data.get("auth_provider", "local"),
                user_data.get("google_id"),
                user_data.get("avatar_url"),
                user_data.get("role", "user"),
                1 if user_data.get("is_active", True) else 0,
                0,
                None,
                None,
                now,
                now,
            ),
        )
        await self.db.commit()

        # Create default settings
        await self.db.execute(
            "INSERT OR IGNORE INTO user_settings (user_id, settings_json, updated_at) VALUES (?, ?, ?)",
            (user_id, json.dumps({}), now),
        )
        await self.db.commit()

        logger.info(f"User created: {user_id} ({user_data['email']})")
        return user_id

    async def get_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        row = await self.db.fetch_one("SELECT * FROM users WHERE id = ?", (user_id,))
        return self._row_to_dict(row) if row else None

    async def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        row = await self.db.fetch_one(
            "SELECT * FROM users WHERE email = ?", (email.lower(),)
        )
        return self._row_to_dict(row) if row else None

    async def get_by_google_id(self, google_id: str) -> Optional[Dict[str, Any]]:
        row = await self.db.fetch_one(
            "SELECT * FROM users WHERE google_id = ?", (google_id,)
        )
        return self._row_to_dict(row) if row else None

    async def update_user(self, user_id: str, updates: Dict[str, Any]) -> bool:
        if not updates:
            return False

        updates["updated_at"] = datetime.now(timezone.utc).isoformat()

        # Build SET clause dynamically
        set_clauses = []
        values = []
        for key, value in updates.items():
            set_clauses.append(f"{key} = ?")
            if key == "is_active":
                values.append(1 if value else 0)
            else:
                values.append(value)

        values.append(user_id)

        conn = await self.db.connection()
        cursor = await conn.execute(
            f"UPDATE users SET {', '.join(set_clauses)} WHERE id = ?",
            tuple(values),
        )
        await conn.commit()
        return cursor.rowcount > 0

    async def increment_failed_logins(self, user_id: str) -> int:
        conn = await self.db.connection()
        await conn.execute(
            """
            UPDATE users
            SET failed_login_attempts = failed_login_attempts + 1,
                updated_at = ?
            WHERE id = ?
            """,
            (datetime.now(timezone.utc).isoformat(), user_id),
        )
        await conn.commit()

        row = await self.db.fetch_one(
            "SELECT failed_login_attempts FROM users WHERE id = ?", (user_id,)
        )
        return row["failed_login_attempts"] if row else 0

    async def reset_failed_logins(self, user_id: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        await self.db.execute(
            """
            UPDATE users
            SET failed_login_attempts = 0, locked_until = NULL, updated_at = ?
            WHERE id = ?
            """,
            (now, user_id),
        )
        await self.db.commit()

    async def set_lockout(self, user_id: str, locked_until: datetime) -> None:
        now = datetime.now(timezone.utc).isoformat()
        await self.db.execute(
            "UPDATE users SET locked_until = ?, updated_at = ? WHERE id = ?",
            (locked_until.isoformat(), now, user_id),
        )
        await self.db.commit()

    async def delete_user(self, user_id: str) -> bool:
        conn = await self.db.connection()
        cursor = await conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        await conn.commit()
        return cursor.rowcount > 0

    @staticmethod
    def _row_to_dict(row: dict) -> Dict[str, Any]:
        """Convert SQLite row to a clean dict, coercing types."""
        if row is None:
            return None
        result = dict(row)
        # Convert integer booleans back
        result["is_active"] = bool(result.get("is_active", 1))
        return result
