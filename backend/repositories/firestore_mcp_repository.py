from typing import List, Optional
from datetime import datetime, timezone
from google.cloud import firestore
from backend.models.mcp_schemas import MCPManifest, CachedToolDefinition, MCPHealthStatus
from backend.repositories.mcp_repository import MCPRepository
from backend.config.settings import settings
import logging

logger = logging.getLogger(__name__)

class FirestoreMCPRepository(MCPRepository):
    def __init__(self):
        # Allow failing fast if ADC not found, consistent with Phase 1
        self.db = firestore.Client(project=settings.GOOGLE_CLOUD_PROJECT)
        self.mcp_col = self.db.collection("mcp_registry")
        self.tools_col = self.db.collection("mcp_tools_cache")

    def register_mcp(self, manifest: MCPManifest) -> None:
        self.mcp_col.document(manifest.mcp_id).set(manifest.model_dump(mode='json'))

    def get_mcp(self, mcp_id: str) -> Optional[MCPManifest]:
        doc = self.mcp_col.document(mcp_id).get()
        if doc.exists:
            return MCPManifest(**doc.to_dict())
        return None

    def list_mcps(self) -> List[MCPManifest]:
        return [MCPManifest(**doc.to_dict()) for doc in self.mcp_col.stream()]

    def update_mcp_health(self, mcp_id: str, status: MCPHealthStatus, timestamp: datetime) -> None:
        doc_ref = self.mcp_col.document(mcp_id)
        if doc_ref.get().exists:
            doc_ref.update({
                "health": status,
                "health_updated_at": timestamp.isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            })

    def set_mcp_enabled(self, mcp_id: str, enabled: bool) -> None:
        doc_ref = self.mcp_col.document(mcp_id)
        if doc_ref.get().exists:
            doc_ref.update({
                "is_enabled": enabled,
                "updated_at": datetime.now(timezone.utc).isoformat()
            })

    def cache_tools(self, mcp_id: str, tools: List[CachedToolDefinition]) -> None:
        batch = self.db.batch()
        
        # 1. Delete existing cached tools for this MCP
        existing = self.tools_col.where(filter=firestore.FieldFilter("mcp_id", "==", mcp_id)).stream()
        for doc in existing:
            batch.delete(doc.reference)
            
        # 2. Add new tools
        for tool in tools:
            doc_ref = self.tools_col.document(f"{mcp_id}_{tool.tool_name}")
            batch.set(doc_ref, tool.model_dump(mode='json'))
            
        batch.commit()

    def get_cached_tools(self, mcp_id: Optional[str] = None) -> List[CachedToolDefinition]:
        query = self.tools_col
        if mcp_id:
            query = query.where(filter=firestore.FieldFilter("mcp_id", "==", mcp_id))
            
        docs = query.stream()
        results = []
        now = datetime.now(timezone.utc)
        
        for doc in docs:
            tool = CachedToolDefinition(**doc.to_dict())
            if tool.expires_at > now:
                results.append(tool)
                
        return results
