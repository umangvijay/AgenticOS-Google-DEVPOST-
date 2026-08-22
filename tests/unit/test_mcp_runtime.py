import pytest
import json
from datetime import datetime, timezone, timedelta
from backend.models.mcp_schemas import MCPManifest, MCPTransportType, AuthType, AuthMetadata, MCPHealthStatus, CachedToolDefinition
from backend.repositories.in_memory_mcp_repository import InMemoryMCPRepository
from backend.mcp.tool_policy import ToolPolicy
from backend.mcp.tool_router import ToolRouter, ToolRouterError
from backend.mcp.mcp_client import MCPClientManager

@pytest.fixture
def repo():
    return InMemoryMCPRepository()

@pytest.fixture
def policy():
    return ToolPolicy()

@pytest.fixture
def router(repo, policy):
    return ToolRouter(repo, policy)

@pytest.fixture
def valid_manifest():
    return MCPManifest(
        mcp_id="calc-mcp",
        name="Calculator",
        version="1.0.0",
        endpoint="http://127.0.0.1:8001/mcp",  # Note: The test uses stdio/streamable_http integration
        transport=MCPTransportType.STREAMABLE_HTTP,
        auth=AuthMetadata(type=AuthType.NONE),
        is_enabled=True,
        health=MCPHealthStatus.HEALTHY
    )

@pytest.mark.asyncio
async def test_mcp_manifest_validation(valid_manifest):
    # Tests that Pydantic validates the schema properly
    assert valid_manifest.name == "Calculator"
    assert valid_manifest.transport == MCPTransportType.STREAMABLE_HTTP

@pytest.mark.asyncio
async def test_mcp_registration_and_get(repo, valid_manifest):
    repo.register_mcp(valid_manifest)
    mcp = repo.get_mcp("calc-mcp")
    assert mcp is not None
    assert mcp.name == "Calculator"

@pytest.mark.asyncio
async def test_mcp_enable_disable(repo, valid_manifest):
    repo.register_mcp(valid_manifest)
    repo.set_mcp_enabled("calc-mcp", False)
    mcp = repo.get_mcp("calc-mcp")
    assert not mcp.is_enabled

@pytest.mark.asyncio
async def test_policy_deny_disabled(repo, policy, valid_manifest):
    valid_manifest.is_enabled = False
    repo.register_mcp(valid_manifest)
    
    tool = CachedToolDefinition(
        tool_name="add",
        description="add",
        input_schema={},
        mcp_id="calc-mcp",
        mcp_version="1.0",
        discovered_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
    )
    
    result = policy.is_allowed(tool, valid_manifest)
    assert not result.allowed
    assert "disabled" in result.reason.lower()

@pytest.mark.asyncio
async def test_policy_deny_unhealthy(repo, policy, valid_manifest):
    valid_manifest.health = MCPHealthStatus.UNHEALTHY
    repo.register_mcp(valid_manifest)
    
    tool = CachedToolDefinition(
        tool_name="add",
        description="add",
        input_schema={},
        mcp_id="calc-mcp",
        mcp_version="1.0",
        discovered_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
    )
    
    result = policy.is_allowed(tool, valid_manifest)
    assert not result.allowed
    assert "unhealthy" in result.reason.lower()

@pytest.mark.asyncio
async def test_policy_allow_healthy_enabled(repo, policy, valid_manifest):
    valid_manifest.health = MCPHealthStatus.HEALTHY
    valid_manifest.is_enabled = True
    repo.register_mcp(valid_manifest)
    
    tool = CachedToolDefinition(
        tool_name="add",
        description="add",
        input_schema={},
        mcp_id="calc-mcp",
        mcp_version="1.0",
        discovered_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
    )
    
    result = policy.is_allowed(tool, valid_manifest)
    assert result.allowed

@pytest.mark.asyncio
async def test_tool_catalog_caching(repo):
    now = datetime.now(timezone.utc)
    tool = CachedToolDefinition(
        tool_name="add",
        description="add",
        input_schema={},
        mcp_id="calc-mcp",
        mcp_version="1.0",
        discovered_at=now,
        expires_at=now + timedelta(hours=1)
    )
    
    repo.cache_tools("calc-mcp", [tool])
    cached = repo.get_cached_tools("calc-mcp")
    assert len(cached) == 1
    assert cached[0].tool_name == "add"
    
    # Test expiration
    tool.expires_at = now - timedelta(hours=1)
    repo.cache_tools("calc-mcp", [tool])
    cached = repo.get_cached_tools("calc-mcp")
    assert len(cached) == 0

@pytest.mark.asyncio
async def test_tool_router_unknown_tool_rejected(router, repo, valid_manifest):
    repo.register_mcp(valid_manifest)
    # The tool is not in cache, so it's unknown
    with pytest.raises(ToolRouterError) as exc:
        await router.execute_tool("calc-mcp__add", {})
    assert "Unknown tool" in str(exc.value)

@pytest.mark.asyncio
async def test_tool_router_invalid_name_rejected(router):
    with pytest.raises(ToolRouterError) as exc:
        await router.execute_tool("invalidname", {})
    assert "Invalid tool name format" in str(exc.value)

@pytest.mark.asyncio
async def test_auth_credential_ref_resolved():
    manifest = MCPManifest(
        mcp_id="secure-mcp",
        name="Secure",
        version="1.0.0",
        endpoint="http://example",
        transport=MCPTransportType.STREAMABLE_HTTP,
        auth=AuthMetadata(type=AuthType.API_KEY, credential_ref="secret/key")
    )
    headers = MCPClientManager.get_auth_headers(manifest)
    assert "Authorization" in headers
    # Tests that no raw credential was stored in manifest
    assert "mocked-secret-for-secret/key" in headers["Authorization"]
