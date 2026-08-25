"""
AgentOS — SQLite Settings Repository

Per-user settings with JSON merge semantics.
"""

import json
import logging
from typing import Dict, Any
from datetime import datetime, timezone

from backend.repositories.base import BaseSettingsRepository
from backend.repositories.sqlite.database import DatabaseManager

logger = logging.getLogger(__name__)

# Default settings for new users
DEFAULT_SETTINGS = {
    "autonomy_level": 1,          # L1: ask before writes
    "theme": "dark",
    "notifications_email": False,
    "notifications_approval": True,
    "daily_token_limit": 1_000_000,
}


class SQLiteSettingsRepository(BaseSettingsRepository):

    def __init__(self, db: DatabaseManager):
        self.db = db

    async def get_settings(self, user_id: str) -> Dict[str, Any]:
        row = await self.db.fetch_one(
            "SELECT settings_json FROM user_settings WHERE user_id = ?",
            (user_id,),
        )
        if row:
            stored = json.loads(row["settings_json"])
            # Merge with defaults so new settings keys are always present
            return {**DEFAULT_SETTINGS, **stored}
        return dict(DEFAULT_SETTINGS)

    async def update_settings(self, user_id: str, updates: Dict[str, Any]) -> None:
        now = datetime.now(timezone.utc).isoformat()

        # Get existing
        existing = await self.get_settings(user_id)
        merged = {**existing, **updates}

        await self.db.execute(
            """
            INSERT INTO user_settings (user_id, settings_json, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                settings_json = excluded.settings_json,
                updated_at = excluded.updated_at
            """,
            (user_id, json.dumps(merged), now),
        )
        await self.db.commit()
