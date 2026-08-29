from google.adk.agents.llm_agent import LlmAgent
from google.adk.models.google_llm import Gemini
from backend.config.settings import settings
from backend.services.llm_context import gemini_adk_kwargs
from backend.models.schemas import WorkflowDefinition

CORE_NODES_DOC = """
Deterministic core nodes (set the task's "agent" field to the node name, no LLM involved):
- core.http  — real HTTP request. input_data: {"url", "method", "headers"?, "body"?, "timeout"?}
- core.set   — emit static/derived fields. input_data: {"fields": {...}}
- core.if    — branch. input_data: {"condition": "<expression or true/false>"}. Downstream tasks are skipped when false.
- core.merge — merge the outputs of all dependency tasks. input_data: {}
- core.loop  — extract a list. input_data: {"items": [...]} or {"field": "<task_id>.<path>"}
- core.email  — send a real email via the user's SMTP account. input_data: {"to", "subject", "body", "html"?}
- core.health — live website/API health probe. input_data: {"url": "https://..."}
- core.chat  — model-written reply. input_data: {"prompt": "..."}
- core.mcp_build — build an MCP for ANY app from a description or OpenAPI URL. input_data: {"method": "prompt"|"url"|"spec"|"website", "source": "<description or URL>", "name"?}

AI agent tasks (set "agent" to "OrchestratorAgent") can:
- call any catalog tool, or build a missing integration for ANY app/API from docs/OpenAPI/description
- browse any public website (login + actions) with stored credentials
- send email, check site health, debug source code, generate a website or small app as files
- create/score/tailor ATS resumes, research, and produce deliverables
For browser, resume, debug, or generation work, create an OrchestratorAgent task with a precise
description and timeout_seconds of at least 180. Use core.http / core.health / core.email only when
the exact URL or email content is already known.

Reference an earlier task's output anywhere in input_data with {{ tasks.<task_id>.output.<path> }}.
"""


def get_planner_agent(catalog_json: str = "[]") -> LlmAgent:
    llm = Gemini(
        model=settings.GEMINI_MODEL,
        client_kwargs=gemini_adk_kwargs(),
    )

    instruction = f"""You are the Planner Agent. Given an Intent, produce a structured workflow definition (DAG) that accomplishes it.

{CORE_NODES_DOC}

Live tool catalog available to OrchestratorAgent tasks (each entry has agent_tool_name and input_schema):
{catalog_json}

Rules:
- Every task needs a unique short task_id (e.g. "fetch_data", "summarize").
- Use dependencies to order tasks; independent tasks may run in parallel.
- Prefer core.http ONLY for plain HTTP calls with a known absolute URL in the intent; use OrchestratorAgent when a matching tool exists in the catalog above.
- CRITICAL: core.http tasks MUST include a non-empty input_data with at least "url" and "method" (e.g. {{"url": "https://api.example.com/data", "method": "GET"}}). Copy the URL directly from the intent target field.
- If the goal needs ANY application that has no tool in the catalog, use core.mcp_build. method "url" for an OpenAPI/Swagger URL; method "website" for a site with no public API (example.com, login/SPA); method "prompt" for a named HTTP API (GitHub, Open-Meteo, PokeAPI). Then add OrchestratorAgent that depends on that build when the user asked to use the tools.
- For login, browsing, filling forms, or doing work on a website: OrchestratorAgent with timeout_seconds of at least 300. Never use core.http GET on a login page.
- For generating a website or app as files: OrchestratorAgent (generate_project). Do not reduce that to core.email.
- Email is optional. Never plan email-only for a website, app, browse, or MCP-use goal.
- For "check if X is up / site health", prefer core.health with the URL.
- Keep the DAG minimal: do not add tasks the goal does not require.
"""
    
    return LlmAgent(
        name="PlannerAgent",
        instruction=instruction,
        model=llm,
        output_schema=WorkflowDefinition
    )
