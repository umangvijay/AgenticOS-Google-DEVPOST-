import pytest
from backend.models.mcp_schemas import MCPManifest, MCPTransportType, AuthType, AuthMetadata, MCPHealthStatus
from backend.repositories.in_memory_mcp_repository import InMemoryMCPRepository
from backend.mcp.tool_policy import ToolPolicy
from backend.mcp.tool_router import ToolRouter
from backend.mcp.health_checker import HealthChecker

@pytest.mark.asyncio
async def test_real_mcp_integration():
    """
    This test assumes the calculator_mcp_server.py is running on port 8001.
    """
    repo = InMemoryMCPRepository()
    policy = ToolPolicy()
    router = ToolRouter(repo, policy)
    checker = HealthChecker(repo)
    
    # 1. Register the MCP
    manifest = MCPManifest(
        mcp_id="calc-mcp",
        name="Calculator",
        version="1.0.0",
        endpoint="http://127.0.0.1:8001/mcp/sse",
        transport=MCPTransportType.STREAMABLE_HTTP,
        auth=AuthMetadata(type=AuthType.NONE),
        is_enabled=True,
    )
    repo.register_mcp(manifest)
    
    # 2. Health check (This should discover tools and cache them)
    await checker.check_all()
    
    mcp = repo.get_mcp("calc-mcp")
    assert mcp.health == MCPHealthStatus.HEALTHY
    
    # 3. Check catalog
    catalog = await router.get_tool_catalog()
    assert len(catalog) == 2
    tool_names = [t["name"] for t in catalog]
    assert "add" in tool_names
    
    # 4. Invoke tool via router
    result = await router.execute_tool("calc-mcp__add", {"a": 10, "b": 20})
    
    # result is a string if it's TextContent
    # actually, mcp client returns a list of ToolResultContent. We need to assert its text.
    text_content = result[0].text if hasattr(result[0], 'text') else str(result)
    assert text_content == "30"
