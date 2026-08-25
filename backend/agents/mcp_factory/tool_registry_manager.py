import uuid
import logging
from datetime import datetime, timezone
from backend.repositories.mcp_repository import MCPRepository

logger = logging.getLogger(__name__)

class ToolRegistryManager:
    """
    Manages the lifecycle of MCP tools: draft -> pending-review -> active -> disabled.
    """
    
    def __init__(self, mcp_repo: MCPRepository):
        self.mcp_repo = mcp_repo

    async def register_mcp(self, name: str, description: str, code: str, trust_tier: str, tools_list: list) -> str:
        """
        Registers a new MCP in the repository and stores its code.
        """
        mcp_id = str(uuid.uuid4())
        
        # Save code to disk (in a real production system this would be in cloud storage)
        from pathlib import Path
        import os
        base_dir = Path("data/generated_mcps")
        base_dir.mkdir(parents=True, exist_ok=True)
        code_path = base_dir / f"{mcp_id}.py"
        code_path.write_text(code)
        
        # Register in DB
        is_enabled = True if trust_tier == "verified" else False
        
        await self.mcp_repo.register_mcp({
            "mcp_id": mcp_id,
            "name": name,
            "description": description,
            "trust_tier": trust_tier,
            "is_enabled": is_enabled,
            "config": {},
            "code_path": str(code_path)
        })
        
        # Register tools
        for t in tools_list:
            await self.mcp_repo.register_tool({
                "tool_id": str(uuid.uuid4()),
                "mcp_id": mcp_id,
                "name": t.get("name", "unknown"),
                "description": t.get("description", ""),
                "input_schema": t.get("inputSchema", {})
            })
            
        logger.info(f"Registered MCP {mcp_id} ('{name}') with {len(tools_list)} tools.")
        return mcp_id
