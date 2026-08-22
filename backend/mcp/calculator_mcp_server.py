import uvicorn
from starlette.applications import Starlette
from starlette.routing import Mount
import contextlib
from mcp.server import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager, StreamableHTTPASGIApp
from mcp.types import Tool, TextContent, CallToolResult
import typing

async def list_tools_handler(ctx, request_params) -> typing.Any:
    # Actually, it expects types.ListToolsResult
    from mcp.types import ListToolsResult
    return ListToolsResult(tools=[
        Tool(
            name="add",
            description="Adds two numbers.",
            input_schema={
                "type": "object",
                "properties": {
                    "a": {"type": "number"},
                    "b": {"type": "number"}
                },
                "required": ["a", "b"]
            }
        ),
        Tool(
            name="subtract",
            description="Subtracts b from a.",
            input_schema={
                "type": "object",
                "properties": {
                    "a": {"type": "number"},
                    "b": {"type": "number"}
                },
                "required": ["a", "b"]
            }
        )
    ])

async def call_tool_handler(ctx, request_params) -> CallToolResult:
    name = request_params.name
    arguments = request_params.arguments
    if name == "add":
        result = arguments["a"] + arguments["b"]
        return CallToolResult(content=[TextContent(type="text", text=str(result))])
    elif name == "subtract":
        result = arguments["a"] - arguments["b"]
        return CallToolResult(content=[TextContent(type="text", text=str(result))])
    else:
        raise ValueError(f"Unknown tool: {name}")

app = Server(
    "calculator-server",
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

starlette_app = Starlette(
    routes=[
        Mount("/mcp", app=asgi_app)
    ],
    lifespan=lifespan
)

if __name__ == "__main__":
    uvicorn.run(starlette_app, host="127.0.0.1", port=8001)
