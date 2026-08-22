import httpx2
import json
import uvicorn
import contextlib
from starlette.applications import Starlette
from starlette.routing import Mount
from starlette.requests import Request
from starlette.responses import JSONResponse
from mcp.server import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager, StreamableHTTPASGIApp
from mcp.types import Tool, TextContent, CallToolResult
from backend.repositories.mcp_repository import MCPRepository
from backend.repositories.in_memory_mcp_repository import InMemoryMCPRepository
from backend.mcp.builder.openapi_parser import OpenAPIParser

# The Proxy uses a globally configured repository instance
_repo = InMemoryMCPRepository()

def get_proxy_repo() -> MCPRepository:
    return _repo

async def list_tools_handler(ctx, request_params):
    # ctx.session has the context, but streamable http doesn't easily expose the original request path in list_tools
    # Since this is a centralized proxy, we need a way to know WHICH mcp_id we are serving.
    # We can inject mcp_id into the MCP arguments, or the proxy URL could be /mcp/{mcp_id}.
    # For now, we will return all cached tools from ALL enabled dynamic connectors!
    from mcp.types import ListToolsResult
    repo = get_proxy_repo()
    all_tools = []
    
    # In a real environment, this proxy might be spun up per-tenant or we use routing.
    # To strictly follow Phase 4: the proxy dynamically maps. 
    for manifest in repo.list_mcps():
        if manifest.is_enabled:
            cached = repo.get_cached_tools(manifest.mcp_id)
            for c in cached:
                all_tools.append(Tool(
                    name=f"{manifest.mcp_id}__{c.tool_name}", # Unique name in proxy namespace
                    description=c.description,
                    inputSchema=c.input_schema
                ))
    return ListToolsResult(tools=all_tools)

async def call_tool_handler(ctx, request_params) -> CallToolResult:
    # Tool names are prefixed like: `mcp_id__tool_name`
    full_name = request_params.name
    arguments = request_params.arguments
    
    if "__" not in full_name:
        raise ValueError(f"Invalid tool name format for proxy: {full_name}")
        
    mcp_id, tool_name = full_name.split("__", 1)
    repo = get_proxy_repo()
    manifest = repo.get_mcp(mcp_id)
    if not manifest or not manifest.is_enabled:
        raise ValueError(f"MCP {mcp_id} is not enabled or does not exist")
        
    cached_tools = repo.get_cached_tools(mcp_id)
    tool_def = next((t for t in cached_tools if t.tool_name == tool_name), None)
    if not tool_def:
        raise ValueError(f"Tool {tool_name} not found in {mcp_id}")
        
    # We need the normalized operation to know HTTP method, path, and server
    # We re-parse from source_uri or cache. For safety and determinism, we fetch it from source
    parser = OpenAPIParser()
    api_model = parser.parse_file(manifest.source_uri)
    
    from backend.mcp.builder.schema_generator import SchemaGenerator
    gen = SchemaGenerator()
    target_op = next((op for op in api_model.operations if gen._normalize_name(op.operation_id) == tool_name), None)
    
    if not target_op:
        raise ValueError("Operation mismatch during proxy resolution")
        
    # Target URL construction
    base_url = target_op.servers[0].url if target_op.servers else api_model.servers[0].url if api_model.servers else ""
    # Revalidate SSRF on actual execution
    parser._validate_ssrf(base_url)
    
    path = target_op.path
    query_params = {}
    headers = {}
    json_body = None
    
    for param in target_op.parameters:
        val = arguments.get(param.name)
        if val is None:
            if param.required:
                raise ValueError(f"Missing required parameter: {param.name}")
            continue
            
        if param.in_ == "path":
            path = path.replace(f"{{{param.name}}}", str(val))
        elif param.in_ == "query":
            query_params[param.name] = val
        elif param.in_ == "header":
            headers[param.name] = str(val)
            
    if target_op.request_body and "request_body" in arguments:
        json_body = arguments["request_body"]
    else:
        # Check if flat properties were merged
        body_data = {}
        for k, v in arguments.items():
            if not any(p.name == k for p in target_op.parameters):
                body_data[k] = v
        if body_data:
            json_body = body_data

    # Security Injection (NEVER forward MCP tokens)
    # 1. Clear any proxy-received authorization (which shouldn't exist since we use StreamableHTTP without auth here usually)
    if "Authorization" in headers:
        del headers["Authorization"]
        
    # 2. Inject specific credential from manifest
    if manifest.auth and manifest.auth.credential_ref:
        # Mock Secret Manager resolution
        resolved_secret = f"secret-for-{manifest.auth.credential_ref}"
        
        # Apply based on tool's auth requirement
        if tool_def.auth_requirements:
            auth_req = tool_def.auth_requirements[0] # taking first for simplicity
            if auth_req.auth_scheme.lower() == "bearer" or "oauth" in auth_req.auth_scheme.lower():
                headers["Authorization"] = f"Bearer {resolved_secret}"
            elif auth_req.auth_scheme.lower() == "apikey":
                headers["X-API-Key"] = resolved_secret
            else:
                headers["Authorization"] = resolved_secret
        else:
            # Fallback
            headers["Authorization"] = f"Bearer {resolved_secret}"

    url = f"{base_url.rstrip('/')}{path}"
    
    async with httpx2.AsyncClient(follow_redirects=False) as client:
        # SSRF Redirect protection via httpx follow_redirects=False 
        try:
            response = await client.request(
                method=target_op.http_method,
                url=url,
                params=query_params,
                headers=headers,
                json=json_body
            )
            
            # Handle Redirects explicitly if needed (revalidating destination)
            if response.status_code in (301, 302, 307, 308):
                redirect_url = response.headers.get("Location")
                parser._validate_ssrf(redirect_url)
                # We could follow manually, but for safety in V1, return redirect error
                raise RuntimeError(f"Redirection strictly blocked for security: {redirect_url}")
                
            response.raise_for_status()
            result_text = response.text
        except httpx2.HTTPError as e:
            result_text = f"API Error: {str(e)}"
            
    return CallToolResult(content=[TextContent(type="text", text=result_text)])

app = Server(
    "openapi-mcp-proxy",
    version="1.0.0",
    on_list_tools=list_tools_handler,
    on_call_tool=call_tool_handler
)

manager = StreamableHTTPSessionManager(app)
asgi_app = StreamableHTTPASGIApp(manager)

@contextlib.asynccontextmanager
async def lifespan(app_instance):
    async with manager.run():
        yield

proxy_app = Starlette(
    routes=[
        Mount("/mcp", app=asgi_app)
    ],
    lifespan=lifespan
)

if __name__ == "__main__":
    uvicorn.run(proxy_app, host="127.0.0.1", port=8002)
