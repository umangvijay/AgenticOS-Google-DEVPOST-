"""
AgentOS — SQLite MCP Repository

Register, list, cache tools, manage trust tiers and health status.
"""

import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from backend.repositories.base import BaseMCPRepository
from backend.repositories.sqlite.database import DatabaseManager

logger = logging.getLogger(__name__)


class SQLiteMCPRepository(BaseMCPRepository):

    def __init__(self, db: DatabaseManager):
        self.db = db

    async def register_mcp(self, manifest_data: Dict[str, Any]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        m = manifest_data
        await self.db.execute(
            """
            INSERT INTO mcps (
                mcp_id, name, version, endpoint, transport, auth_json, scopes,
                health, health_updated_at, state, spec_hash, spec_version,
                source_uri, built_at, owner, is_enabled, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(mcp_id) DO UPDATE SET
                name = excluded.name,
                version = excluded.version,
                endpoint = excluded.endpoint,
                transport = excluded.transport,
                auth_json = excluded.auth_json,
                scopes = excluded.scopes,
                state = excluded.state,
                spec_hash = excluded.spec_hash,
                spec_version = excluded.spec_version,
                source_uri = excluded.source_uri,
                built_at = excluded.built_at,
                updated_at = excluded.updated_at
            """,
            (
                m["mcp_id"],
                m["name"],
                m["version"],
                m["endpoint"],
                m["transport"],
                json.dumps(m.get("auth", {})),
                json.dumps(m.get("scopes", [])),
                m.get("health", "UNKNOWN"),
                m.get("health_updated_at"),
                m.get("state", "DRAFT"),
                m.get("spec_hash"),
                m.get("spec_version"),
                m.get("source_uri"),
                m.get("built_at"),
                m.get("owner", "system"),
                1 if m.get("is_enabled", True) else 0,
                m.get("created_at", now),
                now,
            ),
        )
        await self.db.commit()

    async def get_mcp(self, mcp_id: str) -> Optional[Dict[str, Any]]:
        row = await self.db.fetch_one("SELECT * FROM mcps WHERE mcp_id = ?", (mcp_id,))
        return self._row_to_dict(row) if row else None

    async def list_mcps(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if user_id:
            rows = await self.db.fetch_all(
                "SELECT * FROM mcps WHERE owner = ? OR owner = 'system' ORDER BY created_at DESC",
                (user_id,),
            )
        else:
            rows = await self.db.fetch_all("SELECT * FROM mcps ORDER BY created_at DESC")
        return [self._row_to_dict(r) for r in rows]

    async def update_mcp_health(self, mcp_id: str, status: str, timestamp: datetime) -> None:
        await self.db.execute(
            "UPDATE mcps SET health = ?, health_updated_at = ?, updated_at = ? WHERE mcp_id = ?",
            (status, timestamp.isoformat(), datetime.now(timezone.utc).isoformat(), mcp_id),
        )
        await self.db.commit()

    async def set_mcp_enabled(self, mcp_id: str, enabled: bool) -> None:
        await self.db.execute(
            "UPDATE mcps SET is_enabled = ?, updated_at = ? WHERE mcp_id = ?",
            (1 if enabled else 0, datetime.now(timezone.utc).isoformat(), mcp_id),
        )
        await self.db.commit()

    async def update_mcp_state(self, mcp_id: str, state: str) -> None:
        await self.db.execute(
            "UPDATE mcps SET state = ?, updated_at = ? WHERE mcp_id = ?",
            (state, datetime.now(timezone.utc).isoformat(), mcp_id),
        )
        await self.db.commit()

    async def delete_mcp(self, mcp_id: str) -> bool:
        conn = await self.db.connection()
        # Cascade deletes mcp_tools via FK
        cursor = await conn.execute("DELETE FROM mcps WHERE mcp_id = ?", (mcp_id,))
        await conn.commit()
        return cursor.rowcount > 0

    async def cache_tools(self, mcp_id: str, tools: List[Dict[str, Any]]) -> None:
        conn = await self.db.connection()
        # Clear existing cache for this MCP
        await conn.execute("DELETE FROM mcp_tools WHERE mcp_id = ?", (mcp_id,))
        # Insert new tools
        for tool in tools:
            await conn.execute(
                """
                INSERT INTO mcp_tools (
                    tool_name, description, input_schema, mcp_id, mcp_version,
                    discovered_at, expires_at, auth_requirements, risk_level
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tool["tool_name"],
                    tool["description"],
                    json.dumps(tool["input_schema"]),
                    mcp_id,
                    tool["mcp_version"],
                    tool["discovered_at"],
                    tool["expires_at"],
                    json.dumps(tool.get("auth_requirements", [])),
                    tool.get("risk_level", 4),
                ),
            )
        await conn.commit()

    async def get_cached_tools(self, mcp_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if mcp_id:
            rows = await self.db.fetch_all(
                "SELECT * FROM mcp_tools WHERE mcp_id = ?", (mcp_id,)
            )
        else:
            rows = await self.db.fetch_all("SELECT * FROM mcp_tools")

        results = []
        for row in rows:
            r = dict(row)
            r["input_schema"] = json.loads(r.get("input_schema", "{}"))
            r["auth_requirements"] = json.loads(r.get("auth_requirements", "[]"))
            results.append(r)
        return results

    @staticmethod
    def _row_to_dict(row: dict) -> Optional[Dict[str, Any]]:
        if not row:
            return None
        result = dict(row)
        result["auth"] = json.loads(result.pop("auth_json", "{}"))
        result["scopes"] = json.loads(result.get("scopes", "[]"))
        result["is_enabled"] = bool(result.get("is_enabled", 1))
        return result
