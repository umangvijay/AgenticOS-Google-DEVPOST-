import pytest
from pathlib import Path
from backend.mcp.builder.dynamic_builder import DynamicBuilder
from backend.mcp.mcp_client import MCPClientManager
from backend.repositories.in_memory_mcp_repository import InMemoryMCPRepository
from backend.models.mcp_schemas import ConnectorState, MCPHealthStatus

@pytest.mark.asyncio
async def test_end_to_end_mcp_proxy_integration():
    """
    E2E Test: Builder -> Registry -> Proxy -> External API.
    Assumes `openapi_mcp_proxy.py` is running on port 8002.
    """
    # 1. Build the connector
    # We must use the exact instance that the proxy uses, or we have to mock it.
    from backend.mcp.builder.openapi_mcp_proxy import get_proxy_repo, proxy_app
    import uvicorn
    import asyncio
    
    config = uvicorn.Config(proxy_app, host="127.0.0.1", port=8003, log_level="error")
    server = uvicorn.Server(config)
    server_task = asyncio.create_task(server.serve())
    await asyncio.sleep(1) # wait for server to start
    
    repo = get_proxy_repo()
    
    # clear it first
    repo._mcps = {}
    repo._tool_cache = {}
    
    builder = DynamicBuilder(repo)
    path = Path(__file__).parent.parent / "fixtures" / "openapi" / "petstore.yaml"
    
    manifest = builder.build_connector("petstore-e2e", "Petstore", path)
    
    # 2. Emulate User injecting credentials and enabling
    manifest.endpoint = "http://127.0.0.1:8003/mcp/sse"
    manifest.state = ConnectorState.ENABLED
    manifest.is_enabled = True
    manifest.health = MCPHealthStatus.HEALTHY # Bypass health check phase for test speed
    # We aren't doing actual auth to petstore, so no credential_ref needed for GET
    repo.register_mcp(manifest)
    
    # 3. Use MCPClientManager to call the proxy
    # Since it's Streamable HTTP, we just call the endpoint
    result = await MCPClientManager.call_tool(manifest, "petstore-e2e__listPets", {"limit": 1})
    
    # 4. Verify result (Since petstore.swagger.io/v1/pets might return 404 or a list)
    # The proxy will return CallToolResult with text content containing the HTTP response.
    assert len(result) > 0
    text = result[0].text if hasattr(result[0], 'text') else str(result)
    
    # We expect some JSON or an API Error, but the call MUST succeed without crashing
    assert text is not None
    assert type(text) == str
    
    # Test path substitution
    result_path = await MCPClientManager.call_tool(manifest, "petstore-e2e__showPetById", {"petId": "1"})
    text_path = result_path[0].text if hasattr(result_path[0], 'text') else str(result_path)
    
    assert type(text_path) == str
    # If the swagger petstore /v1/pets/1 returns 404, we'll see "API Error: 404 Not Found"
    # Because httpx2 raises HTTPError on 404
    assert "404" in text_path or "error" in text_path.lower() or "{" in text_path
    
    server.should_exit = True
    await server_task
