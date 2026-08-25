from typing import Optional, Dict, Any, List
from google.cloud import firestore
from backend.repositories.base import BaseMCPRepository
from backend.repositories.firestore.database import FirestoreDB
from backend.models.mcp_schemas import MCPManifest, CachedToolDefinition

class FirestoreMCPRepository(BaseMCPRepository):
    """Firestore implementation of BaseMCPRepository."""

    async def _get_db(self):
        return await FirestoreDB.get_client()

    async def register_mcp(self, manifest: MCPManifest) -> None:
        db = await self._get_db()
        await db.collection("mcps").document(manifest.mcp_id).set(manifest.model_dump(mode="json"))

    async def get_mcp(self, mcp_id: str) -> Optional[MCPManifest]:
        db = await self._get_db()
        doc = await db.collection("mcps").document(mcp_id).get()
        if doc.exists:
            return MCPManifest(**doc.to_dict())
        return None

    async def list_mcps(self, limit: int = 50, offset: int = 0) -> List[MCPManifest]:
        db = await self._get_db()
        query = db.collection("mcps").limit(limit)
        mcps = []
        async for doc in query.stream():
            mcps.append(MCPManifest(**doc.to_dict()))
        return mcps

    async def update_mcp_status(self, mcp_id: str, is_active: bool) -> None:
        db = await self._get_db()
        await db.collection("mcps").document(mcp_id).update({"is_active": is_active})

    async def cache_tools(self, tools: List[CachedToolDefinition]) -> None:
        if not tools:
            return
        db = await self._get_db()
        batch = db.batch()
        for t in tools:
            # We use a compound ID to ensure uniqueness
            doc_id = f"{t.mcp_id}_{t.tool_name}"
            ref = db.collection("mcp_tools").document(doc_id)
            batch.set(ref, t.model_dump(mode="json"))
        await batch.commit()

    async def get_cached_tools(self, mcp_id: Optional[str] = None) -> List[CachedToolDefinition]:
        db = await self._get_db()
        query = db.collection("mcp_tools")
        if mcp_id:
            query = query.where("mcp_id", "==", mcp_id)
            
        tools = []
        async for doc in query.stream():
            tools.append(CachedToolDefinition(**doc.to_dict()))
        return tools
