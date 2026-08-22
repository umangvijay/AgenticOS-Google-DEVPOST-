import os
import asyncio
from typing import Dict, Any, List, Optional
from mcp.client.streamable_http import streamable_http_client
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession
from backend.models.mcp_schemas import MCPManifest, MCPTransportType, AuthType, CachedToolDefinition
from datetime import datetime, timezone

class MCPClientManager:
    """Manages MCP Client connections utilizing the official python SDK."""

    @classmethod
    def get_auth_headers(cls, manifest: MCPManifest) -> Dict[str, str]:
        headers = {}
        if manifest.auth.type == AuthType.API_KEY and manifest.auth.credential_ref:
            # In Phase 3, credential_ref acts as an identifier to fetch the secret from Secret Manager
            # We mock the Secret Manager resolution here
            api_key = f"mocked-secret-for-{manifest.auth.credential_ref}"
            headers["Authorization"] = f"Bearer {api_key}"
        return headers

    @classmethod
    async def discover_tools(cls, manifest: MCPManifest) -> List[CachedToolDefinition]:
        """Connect to MCP, initialize, and fetch tools list."""
        tools = []
        if manifest.transport == MCPTransportType.STREAMABLE_HTTP:
            headers = cls.get_auth_headers(manifest)
            import httpx2
            client = httpx2.AsyncClient(headers=headers)
            async with streamable_http_client(manifest.endpoint, http_client=client) as streams:
                async with ClientSession(streams[0], streams[1]) as session:
                    await session.initialize()
                    result = await session.list_tools()
                    tools = result.tools
        elif manifest.transport == MCPTransportType.STDIO:
            # endpoint is the executable path
            server_params = StdioServerParameters(command=manifest.endpoint, args=[])
            async with stdio_client(server_params) as streams:
                async with ClientSession(streams[0], streams[1]) as session:
                    await session.initialize()
                    result = await session.list_tools()
                    tools = result.tools

        # Convert to CachedToolDefinition
        cached_tools = []
        now = datetime.now(timezone.utc)
        from datetime import timedelta
        # Cache for 1 hour
        expires_at = now + timedelta(hours=1)
        
        for t in tools:
            cached_tools.append(CachedToolDefinition(
                tool_name=t.name,
                description=t.description,
                input_schema=t.input_schema,
                mcp_id=manifest.mcp_id,
                mcp_version=manifest.version,
                discovered_at=now,
                expires_at=expires_at
            ))
            
        return cached_tools

    @classmethod
    async def call_tool(cls, manifest: MCPManifest, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Connect to MCP, initialize, and call a tool."""
        if manifest.transport == MCPTransportType.STREAMABLE_HTTP:
            headers = cls.get_auth_headers(manifest)
            import httpx2
            client = httpx2.AsyncClient(headers=headers)
            async with streamable_http_client(manifest.endpoint, http_client=client) as streams:
                async with ClientSession(streams[0], streams[1]) as session:
                    await session.initialize()
                    result = await session.call_tool(tool_name, arguments)
                    return result.content
        elif manifest.transport == MCPTransportType.STDIO:
            server_params = StdioServerParameters(command=manifest.endpoint, args=[])
            async with stdio_client(server_params) as streams:
                async with ClientSession(streams[0], streams[1]) as session:
                    await session.initialize()
                    result = await session.call_tool(tool_name, arguments)
                    return result.content
        else:
            raise ValueError(f"Unknown transport {manifest.transport}")
