import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ToolRegistryManager:
    def __init__(self, mcp_repo):
        self.mcp_repo = mcp_repo

    async def register_mcp(
        self,
        name: str,
        description: str,
        tools_list: list,
        *,
        owner: str = "system",
        trust_tier: str = "pending_review",
        source_type: str = "openapi",
        source_uri: Optional[str] = None,
        spec_json: Optional[str] = None,
        spec_hash: Optional[str] = None,
        spec_version: str = "1.0.0",
        auth: Optional[Dict[str, Any]] = None,
        is_enabled: bool = False,
        mcp_id: Optional[str] = None,
    ) -> str:
        mcp_id = mcp_id or str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        tools_payload: List[Dict[str, Any]] = []
        for t in tools_list:
            if hasattr(t, "model_dump"):
                tools_payload.append(t.model_dump(mode="json"))
            else:
                tools_payload.append(dict(t))

        await self.mcp_repo.register_mcp({
            "mcp_id": mcp_id,
            "name": name,
            "description": description,
            "version": spec_version,
            "endpoint": f"internal://openapi/{mcp_id}",
            "transport": "internal",
            "auth": auth or {"type": "API_KEY"},
            "scopes": [],
            "health": "UNKNOWN",
            "state": "HEALTHY" if is_enabled else "PENDING_CREDENTIALS",
            "spec_hash": spec_hash,
            "spec_version": spec_version,
            "source_uri": source_uri,
            "built_at": now,
            "owner": owner,
            "is_enabled": is_enabled,
            "trust_tier": trust_tier,
            "source_type": source_type,
            "spec_json": spec_json,
        })
        await self.mcp_repo.cache_tools(mcp_id, tools_payload)
        logger.info("Registered MCP %s (%s) with %s tools", mcp_id, name, len(tools_payload))
        return mcp_id
