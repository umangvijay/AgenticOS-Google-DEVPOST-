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
    def get_auth_headers(cls, manifest: MCPManifest, extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        headers = extra_headers or {}
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
            from backend.mcp.sandbox.sandbox_controller import SandboxController
            from backend.mcp.sandbox.audit_logger import audit_logger
            
            import shlex
            parts = shlex.split(manifest.endpoint)
            base_cmd = parts[0] if parts else ""
            args = parts[1:] if len(parts) > 1 else []
            
            docker_cmd, docker_args = SandboxController.apply_docker_sandbox(
                manifest=manifest,
                command=base_cmd,
                args=args
            )
            
            server_params = StdioServerParameters(command=docker_cmd, args=docker_args)
            try:
                async with asyncio.timeout(15): # Python 3.11+
                    async with stdio_client(server_params) as streams:
                        async with ClientSession(streams[0], streams[1]) as session:
                            await session.initialize()
                            result = await session.list_tools()
                            tools = result.tools
            except asyncio.TimeoutError:
                audit_logger.log_sandbox_timeout(manifest.mcp_id, 15)
                raise RuntimeError(f"Sandbox Execution Timeout for {manifest.mcp_id}")
            except Exception as e:
                audit_logger.log_sandbox_violation(manifest.mcp_id, "EXECUTION_ERROR", str(e))
                raise

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
    async def call_tool(cls, manifest: MCPManifest, tool_name: str, arguments: Dict[str, Any], extra_headers: Optional[Dict[str, str]] = None) -> Any:
        """Connect to MCP, initialize, and call a tool."""
        if manifest.transport == MCPTransportType.STREAMABLE_HTTP:
            headers = cls.get_auth_headers(manifest, extra_headers)
            import httpx2
            client = httpx2.AsyncClient(headers=headers)
            async with streamable_http_client(manifest.endpoint, http_client=client) as streams:
                async with ClientSession(streams[0], streams[1]) as session:
                    await session.initialize()
                    result = await session.call_tool(tool_name, arguments)
                    return result.content
        elif manifest.transport == MCPTransportType.STDIO:
            from backend.mcp.sandbox.sandbox_controller import SandboxController
            from backend.mcp.sandbox.audit_logger import audit_logger
            
            import shlex
            parts = shlex.split(manifest.endpoint)
            base_cmd = parts[0] if parts else ""
            args = parts[1:] if len(parts) > 1 else []
            
            docker_cmd, docker_args = SandboxController.apply_docker_sandbox(
                manifest=manifest,
                command=base_cmd,
                args=args
            )
            server_params = StdioServerParameters(command=docker_cmd, args=docker_args)
            
            try:
                async with asyncio.timeout(15):
                    async with stdio_client(server_params) as streams:
                        async with ClientSession(streams[0], streams[1]) as session:
                            await session.initialize()
                            result = await session.call_tool(tool_name, arguments)
                            return result.content
            except asyncio.TimeoutError:
                audit_logger.log_sandbox_timeout(manifest.mcp_id, 15)
                raise RuntimeError(f"Sandbox Execution Timeout calling {tool_name}")
            except Exception as e:
                audit_logger.log_sandbox_violation(manifest.mcp_id, "TOOL_EXECUTION_ERROR", str(e))
                raise e
        else:
            raise ValueError(f"Unknown transport {manifest.transport}")
