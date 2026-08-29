"""Website vs HTTP vs OpenAPI routing for chat MCP builds."""

from backend.engine.direct_plan import plan_from_goal
from backend.engine.mcp_catalog import arguments_for_catalog_tool, pick_catalog_tool, sketch_openapi_from_prompt
from backend.mcp.website_mcp import looks_like_http_api_url, looks_like_website_without_api


def test_example_com_create_tools_is_website():
    goal = "Create MCP tools for https://example.com then open home and summarize the page"
    assert looks_like_website_without_api(goal, "https://example.com")
    plan = plan_from_goal(goal)
    assert plan is not None
    agents = [t.agent for t in plan.tasks]
    assert "core.mcp_build" in agents
    mcp = next(t for t in plan.tasks if t.agent == "core.mcp_build")
    assert mcp.input_data["method"] == "website"


def test_openapi_url_is_url_method():
    goal = "Create MCP tools from https://raw.githubusercontent.com/PokeAPI/pokeapi/master/openapi.yml then list pokemon"
    plan = plan_from_goal(goal)
    mcp = next(t for t in plan.tasks if t.agent == "core.mcp_build")
    assert mcp.input_data["method"] == "url"
    assert "openapi.yml" in mcp.input_data["source"]


def test_github_http_without_openapi_is_prompt():
    goal = "Build MCP tools for GitHub so I can list public events, then list them"
    assert not looks_like_website_without_api(goal, None)
    plan = plan_from_goal(goal)
    mcp = next(t for t in plan.tasks if t.agent == "core.mcp_build")
    assert mcp.input_data["method"] == "prompt"


def test_pokeapi_url_is_http_not_website():
    url = "https://pokeapi.co/api/v2"
    assert looks_like_http_api_url(url)
    assert not looks_like_website_without_api("Create MCP tools for https://pokeapi.co/api/v2", url)


def test_follow_up_reuses_orchestrator():
    prior = "Create MCP tools for https://example.com"
    plan = plan_from_goal("Log in with vault credential bharatenglish and open home / use runOnSite", prior_goal=prior)
    assert plan is not None
    assert plan.tasks[0].agent == "OrchestratorAgent"


def test_sketch_github_events():
    spec = sketch_openapi_from_prompt("Build MCP tools for GitHub so I can list public events")
    assert spec and "api.github.com" in spec
    assert "/events" in spec


def test_pick_catalog_tool_prefers_matching_name():
    catalog = [
        {"name": "runOnSite", "mcp_name": "example.com", "agent_tool_name": "w__runOnSite", "description": "browser"},
        {"name": "list_events", "mcp_name": "GitHub", "agent_tool_name": "g__list_events", "description": "List events"},
    ]
    picked = pick_catalog_tool("list the github events", catalog)
    assert picked["name"] == "list_events"
    args = arguments_for_catalog_tool(
        {"name": "login", "input_schema": {"properties": {"credential_name": {}}, "required": ["credential_name"]}},
        "Log in with vault credential bharatenglish and open home",
    )
    assert args["credential_name"] == "bharatenglish"
