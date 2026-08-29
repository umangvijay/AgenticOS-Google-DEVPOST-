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
                source_uri, built_at, owner, is_enabled, created_at, updated_at,
                description, trust_tier, source_type, spec_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                owner = excluded.owner,
                is_enabled = excluded.is_enabled,
                description = excluded.description,
                trust_tier = excluded.trust_tier,
                source_type = excluded.source_type,
                spec_json = excluded.spec_json,
                updated_at = excluded.updated_at
            """,
            (
                m["mcp_id"],
                m["name"],
                m.get("version", "1.0.0"),
                m.get("endpoint", f"internal://openapi/{m['mcp_id']}"),
                m.get("transport", "internal"),
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
                m.get("description", ""),
                m.get("trust_tier", "pending_review"),
                m.get("source_type", "openapi"),
                m.get("spec_json"),
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

    async def update_mcp_auth(self, mcp_id: str, auth: Dict[str, Any]) -> None:
        await self.db.execute(
            "UPDATE mcps SET auth_json = ?, updated_at = ? WHERE mcp_id = ?",
            (json.dumps(auth), datetime.now(timezone.utc).isoformat(), mcp_id),
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
            auth_reqs = tool.get("auth_requirements", [])
            if auth_reqs and hasattr(auth_reqs[0], "model_dump"):
                auth_reqs = [a.model_dump() if hasattr(a, "model_dump") else a for a in auth_reqs]
            operation = tool.get("operation") or {}
            if hasattr(operation, "model_dump"):
                operation = operation.model_dump()
            risk = tool.get("risk_level", 4)
            if hasattr(risk, "value"):
                risk = risk.value
            discovered = tool.get("discovered_at") or datetime.now(timezone.utc).isoformat()
            expires = tool.get("expires_at") or datetime.now(timezone.utc).isoformat()
            if hasattr(discovered, "isoformat"):
                discovered = discovered.isoformat()
            if hasattr(expires, "isoformat"):
                expires = expires.isoformat()
            await conn.execute(
                """
                INSERT INTO mcp_tools (
                    tool_name, description, input_schema, mcp_id, mcp_version,
                    discovered_at, expires_at, auth_requirements, risk_level, operation_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tool.get("tool_name") or tool.get("name") or "unknown",
                    tool.get("description", ""),
                    json.dumps(tool.get("input_schema") or tool.get("inputSchema") or {}),
                    mcp_id,
                    tool.get("mcp_version", "1.0.0"),
                    discovered,
                    expires,
                    json.dumps(auth_reqs),
                    int(risk) if risk is not None else 4,
                    json.dumps(operation),
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
            r["input_schema"] = json.loads(r.get("input_schema") or "{}")
            r["auth_requirements"] = json.loads(r.get("auth_requirements") or "[]")
            r["operation"] = json.loads(r.get("operation_json") or "{}")
            r["name"] = r.get("tool_name")
            r["inputSchema"] = r["input_schema"]
            results.append(r)
        return results

    async def create_build(self, build: Dict[str, Any]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        await self.db.execute(
            """
            INSERT INTO mcp_builds (
                build_id, user_id, name, method, source, status, stage,
                logs_json, mcp_id, tools_json, error, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                build["build_id"],
                build["user_id"],
                build.get("name") or "",
                build.get("method") or "url",
                build.get("source") or "",
                build.get("status", "queued"),
                build.get("stage", "queued"),
                json.dumps(build.get("logs") or []),
                build.get("mcp_id"),
                json.dumps(build.get("tools") or []),
                build.get("error"),
                now,
                now,
            ),
        )
        await self.db.commit()

    async def update_build(self, build_id: str, updates: Dict[str, Any]) -> None:
        if not updates:
            return
        mapping = {
            "logs": "logs_json",
            "tools": "tools_json",
        }
        set_clauses = []
        values = []
        for key, value in updates.items():
            col = mapping.get(key, key)
            set_clauses.append(f"{col} = ?")
            if key in ("logs", "tools") or isinstance(value, (dict, list)):
                values.append(json.dumps(value))
            else:
                values.append(value)
        values.append(datetime.now(timezone.utc).isoformat())
        values.append(build_id)
        await self.db.execute(
            f"UPDATE mcp_builds SET {', '.join(set_clauses)}, updated_at = ? WHERE build_id = ?",
            tuple(values),
        )
        await self.db.commit()

    async def get_build(self, build_id: str) -> Optional[Dict[str, Any]]:
        row = await self.db.fetch_one("SELECT * FROM mcp_builds WHERE build_id = ?", (build_id,))
        return self._build_row(row) if row else None

    @staticmethod
    def _build_row(row: dict) -> Optional[Dict[str, Any]]:
        if not row:
            return None
        r = dict(row)
        r["logs"] = json.loads(r.pop("logs_json", "[]") or "[]")
        r["tools"] = json.loads(r.pop("tools_json", "[]") or "[]")
        return r

    @staticmethod
    def _row_to_dict(row: dict) -> Optional[Dict[str, Any]]:
        if not row:
            return None
        result = dict(row)
        result["auth"] = json.loads(result.pop("auth_json", None) or "{}")
        scopes_raw = result.get("scopes") or "[]"
        if isinstance(scopes_raw, str):
            try:
                result["scopes"] = json.loads(scopes_raw)
            except json.JSONDecodeError:
                result["scopes"] = []
        elif not isinstance(scopes_raw, list):
            result["scopes"] = []
        result["is_enabled"] = bool(result.get("is_enabled", 1))
        return result
