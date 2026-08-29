from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from backend.repositories.base import BaseMCPRepository
from backend.repositories.firestore.database import FirestoreDB


def _as_dict(value: Any) -> Dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return dict(value)


class FirestoreMCPRepository(BaseMCPRepository):
    """Firestore implementation of BaseMCPRepository."""

    async def _get_db(self):
        return await FirestoreDB.get_client()

    async def register_mcp(self, manifest_data) -> None:
        payload = _as_dict(manifest_data)
        mcp_id = payload.get("mcp_id")
        if not mcp_id:
            raise ValueError("MCP manifest must have 'mcp_id'")
        payload.setdefault("updated_at", datetime.now(timezone.utc).isoformat())
        payload.setdefault("is_enabled", payload.get("is_enabled", True))
        db = await self._get_db()
        await db.collection("mcps").document(mcp_id).set(payload)

    async def get_mcp(self, mcp_id: str) -> Optional[Dict[str, Any]]:
        db = await self._get_db()
        doc = await db.collection("mcps").document(mcp_id).get()
        if doc.exists:
            return doc.to_dict() or {}
        return None

    async def list_mcps(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        db = await self._get_db()
        mcps = []
        async for doc in db.collection("mcps").stream():
            data = doc.to_dict() or {}
            owner = data.get("owner")
            if user_id and owner not in (user_id, "system", None):
                continue
            mcps.append(data)
        return mcps

    async def update_mcp_health(self, mcp_id: str, status: str, timestamp: datetime) -> None:
        db = await self._get_db()
        ts = timestamp.isoformat() if hasattr(timestamp, "isoformat") else str(timestamp)
        await db.collection("mcps").document(mcp_id).update(
            {
                "health": status,
                "health_updated_at": ts,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    async def set_mcp_enabled(self, mcp_id: str, enabled: bool) -> None:
        db = await self._get_db()
        await db.collection("mcps").document(mcp_id).update(
            {
                "is_enabled": bool(enabled),
                "is_active": bool(enabled),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    async def update_mcp_state(self, mcp_id: str, state: str) -> None:
        db = await self._get_db()
        await db.collection("mcps").document(mcp_id).update(
            {
                "state": state,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    async def update_mcp_auth(self, mcp_id: str, auth: Dict[str, Any]) -> None:
        db = await self._get_db()
        await db.collection("mcps").document(mcp_id).update(
            {
                "auth": auth,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    async def delete_mcp(self, mcp_id: str) -> bool:
        db = await self._get_db()
        ref = db.collection("mcps").document(mcp_id)
        snap = await ref.get()
        if not snap.exists:
            return False
        await ref.delete()
        async for doc in db.collection("mcp_tools").where("mcp_id", "==", mcp_id).stream():
            await doc.reference.delete()
        return True

    async def cache_tools(self, mcp_id: str, tools: List[Any] = None) -> None:
        if isinstance(mcp_id, list) and tools is None:
            tools = mcp_id
            mcp_id = None
            if tools:
                first = _as_dict(tools[0])
                mcp_id = first.get("mcp_id")
        tools = tools or []
        db = await self._get_db()
        if mcp_id:
            async for doc in db.collection("mcp_tools").where("mcp_id", "==", mcp_id).stream():
                await doc.reference.delete()
        if not tools:
            return
        batch = db.batch()
        for t in tools:
            payload = _as_dict(t)
            payload.setdefault("mcp_id", mcp_id)
            tool_name = payload.get("tool_name") or payload.get("name") or "unknown"
            payload["tool_name"] = tool_name
            doc_id = f"{payload.get('mcp_id')}_{tool_name}"
            ref = db.collection("mcp_tools").document(doc_id)
            batch.set(ref, payload)
        await batch.commit()

    async def get_cached_tools(self, mcp_id: Optional[str] = None) -> List[Dict[str, Any]]:
        db = await self._get_db()
        query = db.collection("mcp_tools")
        if mcp_id:
            query = query.where("mcp_id", "==", mcp_id)
        tools = []
        async for doc in query.stream():
            tools.append(doc.to_dict() or {})
        return tools

    async def create_build(self, build: Dict[str, Any]) -> None:
        payload = dict(build)
        now = datetime.now(timezone.utc).isoformat()
        payload.setdefault("logs", [])
        payload.setdefault("tools", [])
        payload.setdefault("created_at", now)
        payload["updated_at"] = now
        build_id = payload.get("build_id")
        if not build_id:
            raise ValueError("Build dict must have 'build_id'")
        db = await self._get_db()
        await db.collection("mcp_builds").document(build_id).set(payload)

    async def update_build(self, build_id: str, updates: Dict[str, Any]) -> None:
        if not updates:
            return
        payload = dict(updates)
        payload["updated_at"] = datetime.now(timezone.utc).isoformat()
        db = await self._get_db()
        await db.collection("mcp_builds").document(build_id).update(payload)

    async def get_build(self, build_id: str) -> Optional[Dict[str, Any]]:
        db = await self._get_db()
        doc = await db.collection("mcp_builds").document(build_id).get()
        if doc.exists:
            return doc.to_dict() or {}
        return None
