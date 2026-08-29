import json
from google.adk.agents.llm_agent import LlmAgent
from google.adk.models.google_llm import Gemini
from backend.config.settings import settings
from backend.services.llm_context import gemini_adk_kwargs
from backend.repositories.memory_repository import MemoryRepository
from backend.services.embedding_service import EmbeddingService
from backend.models.resume import Resume
from backend.services.jd_parser_service import JDParserService
from backend.services.resume_tailor_service import ResumeTailorService

def get_orchestrator_agent(tool_router=None, catalog_json: str = "[]", memory_repo: MemoryRepository = None, embedding_service: EmbeddingService = None, user_id: str = "default_user", workflow_context: str = "", execution_context: dict = None) -> LlmAgent:
    llm = Gemini(
        model=settings.GEMINI_MODEL,
        client_kwargs=gemini_adk_kwargs(),
        tools=[{"google_search": {}}]
    )
    
    async def call_external_tool(agent_tool_name: str, arguments_json: str) -> str:
        """Call a tool from the external tool catalog.
        Args:
            agent_tool_name: The agent_tool_name from the catalog (e.g. mcp1__add).
            arguments_json: JSON string containing the arguments according to the tool's input_schema.
        """
        if not tool_router:
            return "Error: ToolRouter not initialized."
        try:
            args = json.loads(arguments_json)
            ctx = {"user_id": user_id, **(execution_context or {})}
            result = await tool_router.execute_tool_safe(agent_tool_name, args, context=ctx)
            return json.dumps(result) if isinstance(result, (dict, list)) else str(result)
        except Exception as e:
            # To bubble up retries/failures to the workflow engine, we MUST raise it!
            raise e

    async def build_integration(api_docs_url_or_description: str, name: str, api_credential_name: str = "") -> str:
        """Build a NEW integration when no tool in the catalog covers the application you need.
        The MCP factory ingests the API docs/OpenAPI spec at the URL (or the plain-text
        description), generates tool schemas, live-tests them, and registers the tools.
        Args:
            api_docs_url_or_description: URL to an OpenAPI spec / API docs page, or a natural-language API description.
            name: Human-readable integration name (the application or API).
            api_credential_name: Optional name of a stored credential (holding an api_key/token)
                to attach so the new tools authenticate to the API (e.g. "stripe").
        Returns: JSON with the build result and the refreshed tool catalog.
        """
        if not tool_router:
            return "Error: ToolRouter not initialized."
        try:
            from backend.agents.mcp_factory.mcp_factory_agent import MCPFactoryAgent
            factory_agent = MCPFactoryAgent(
                tool_router.mcp_repo,
                secrets_repo=getattr(tool_router, "secrets_repo", None),
            )
            source = api_docs_url_or_description.strip()
            from backend.mcp.website_mcp import looks_like_website_without_api
            if looks_like_website_without_api(
                source, url=source if source.startswith(("http://", "https://")) else None
            ):
                method = "website"
            elif source.startswith(("http://", "https://")):
                method = "url"
            else:
                method = "prompt"
            result = await factory_agent.run_build(
                user_id=user_id, method=method, source=source, name=name,
            )
            if result.get("status") == "success" and api_credential_name:
                await tool_router.mcp_repo.update_mcp_auth(
                    result["mcp_id"],
                    {"type": "API_KEY", "credential_ref": f"cred:{api_credential_name}"},
                )
                result["credential_attached"] = api_credential_name
            fresh_catalog = await tool_router.get_tool_catalog(user_id)
            return json.dumps({"build": result, "catalog": fresh_catalog})
        except Exception as e:
            return json.dumps({"build": {"status": "error", "message": str(e)}})

    async def browse_website(goal: str, start_url: str, credential_name: str = "") -> str:
        """Perform human-like work in a real web browser on the user's behalf:
        log in to a website, click buttons, fill forms, complete exercises/tasks,
        and extract information.
        Args:
            goal: Precise description of what to accomplish on the site
                (e.g. "Log in, open today's exercises, and complete each one").
            start_url: The URL to open first (e.g. "https://example.com/login").
            credential_name: Optional name of a stored credential with the site login
                (fields like username/password). Ask the user to store it via the
                Credentials page if it does not exist.
        Returns: JSON with success flag, a result summary, and the audited step list.
        """
        try:
            from backend.services.web_agent import WebAgent
            agent = WebAgent(secrets_repo=getattr(tool_router, "secrets_repo", None))
            outcome = await agent.run(
                goal=goal,
                start_url=start_url,
                user_id=user_id,
                credential_name=credential_name or None,
                max_steps=50,
            )
            return json.dumps(outcome)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    async def send_email(to: str, subject: str, body: str, html: bool = False) -> str:
        """Send a real email on the user's behalf via their configured SMTP account.
        Requires a stored credential named "smtp" (fields: host, port, username, password).
        Args:
            to: Recipient email address (comma-separate for multiple recipients).
            subject: Email subject line.
            body: Email body. Write it fully and professionally — you are writing as the user.
            html: Set true if body is HTML.
        Returns: JSON confirmation or an error explaining what is missing.
        """
        try:
            from backend.services import email_service
            recipients = [addr.strip() for addr in to.split(",") if addr.strip()]
            result = await email_service.send_email(
                getattr(tool_router, "secrets_repo", None),
                user_id, recipients, subject, body, html=html,
            )
            return json.dumps(result)
        except Exception as e:
            return json.dumps({"sent": False, "error": str(e)})

    async def list_stored_credentials() -> str:
        """List the names of credentials the user has stored (site logins, smtp, API keys).
        Values are never revealed. Use this to check whether a login or API key exists
        before calling browse_website, send_email, or build_integration."""
        secrets_repo = getattr(tool_router, "secrets_repo", None)
        if not secrets_repo:
            return json.dumps({"credentials": []})
        try:
            keys = await secrets_repo.list_secret_keys(user_id)
            names = [k[5:] for k in keys if k.startswith("cred:")]
            return json.dumps({"credentials": names})
        except Exception as e:
            return json.dumps({"credentials": [], "error": str(e)})

    async def search_memory(query: str, limit: int = 5) -> str:
        """Search the semantic memory for relevant past context.
        Args:
            query: The search query string.
            limit: Maximum number of results to return.
        """
        if not memory_repo or not embedding_service:
            return "Error: Memory system not initialized."
        try:
            embedding = embedding_service.embed_text(query)
            results = await memory_repo.search_memory(user_id, embedding, limit=limit)
            if not results:
                return "No relevant memory found."
            return json.dumps([
                {"id": r["id"], "content": r["content"], "score": r.get("similarity_score", 0.0)}
                for r in results
            ])
        except Exception as e:
            return f"Error searching memory: {str(e)}"

    async def store_memory(content: str, metadata_json: str = "{}") -> str:
        """Store semantic context into memory for future retrieval.
        Args:
            content: The text content to remember.
            metadata_json: JSON string of structured metadata.
        """
        if not memory_repo or not embedding_service:
            return "Error: Memory system not initialized."
        try:
            metadata = json.loads(metadata_json)
            embedding = embedding_service.embed_text(content)
            doc_id = await memory_repo.store_memory(user_id, content, "semantic", metadata, embedding)
            return f"Memory stored successfully with ID: {doc_id}"
        except Exception as e:
            return f"Error storing memory: {str(e)}"

    async def analyze_resume_ats(resume_json: str, jd_text: str) -> str:
        """Score a structured resume JSON against a job description for ATS match."""
        try:
            from backend.services.resume_builder import score_resume
            return json.dumps(score_resume(resume_json, jd_text))
        except Exception as e:
            return json.dumps({"error": str(e)})

    async def tailor_resume(resume_json: str, jd_text: str, target_job_id: str) -> str:
        """Tailor a master resume to a job description without fabricating facts."""
        try:
            resume = Resume.model_validate_json(resume_json)
            jd = JDParserService().parse_job_description(jd_text)
            tailored = ResumeTailorService().tailor(resume, jd, target_job_id)
            return tailored.model_dump_json()
        except Exception as e:
            return json.dumps({"error": str(e)})

    async def create_resume(profile_text: str, job_description: str = "", tailor: bool = False) -> str:
        """Create an ATS-ready resume from free-form background text (notes, LinkedIn dump, old CV).
        Optionally score and tailor it against a job description.
        Args:
            profile_text: Everything known about the candidate. Do not invent employers or metrics.
            job_description: Optional JD to score (and optionally tailor) against.
            tailor: If true and a JD is provided, rewrite bullets toward the JD without fabricating facts.
        """
        try:
            from backend.services.resume_builder import create_and_score
            result = await create_and_score(profile_text, job_description, tailor=tailor)
            return json.dumps(result)
        except Exception as e:
            return json.dumps({"error": str(e)})

    async def check_website_health(url: str) -> str:
        """Live health check of any public website or HTTP API: DNS, TLS, latency, status, redirects, security headers.
        Args:
            url: Absolute http(s) URL of the site or endpoint to probe.
        """
        try:
            from backend.services.website_health import check_website
            return json.dumps(await check_website(url))
        except Exception as e:
            return json.dumps({"error": str(e), "grade": "down"})

    async def debug_code(source: str, language: str = "python", error_message: str = "", goal: str = "") -> str:
        """Diagnose bugs in source code. Runs a syntax check (Python) plus an LLM diagnosis.
        Does not execute the submitted code.
        Args:
            source: Full source to debug.
            language: Language id (python, javascript, typescript, go, ...).
            error_message: Optional stack trace or error text.
            goal: Optional description of expected behavior.
        """
        try:
            from backend.services.code_debugger import debug_code as _debug
            return json.dumps(await _debug(source, language, error_message, goal))
        except Exception as e:
            return json.dumps({"error": str(e)})

    async def generate_project(brief: str, kind: str = "website", name: str = "", scale: str = "") -> str:
        """Generate a real website or software project as downloadable files.
        Use kind="website" for a static site. Use kind="app" for a local project with README.
        scale: compact (landing), standard (medium), full (large multi-page/app).
        Args:
            brief: What to build, audience, pages/features, look and feel.
            kind: "website" or "app".
            name: Optional short project name.
            scale: compact | standard | full. Infer from the brief if empty.
        """
        try:
            from backend.services.artifact_builder import generate_project as _gen
            lowered = (brief or "").lower()
            chosen = (scale or "").lower().strip()
            if chosen not in ("compact", "standard", "full"):
                if any(w in lowered for w in ("landing", "one page", "single page", "compact")):
                    chosen = "compact"
                elif any(w in lowered for w in ("full app", "large", "production", "multi-page", "complete app", "medium")):
                    chosen = "full"
                else:
                    chosen = "standard"
            return json.dumps(await _gen(user_id, brief, kind=kind, name=name, scale=chosen))
        except Exception as e:
            return json.dumps({"error": str(e)})

    instruction = f"""You are the Orchestrator Agent. Execute the given task using the best available capability.

External tool catalog (APIs already connected for this user):
{catalog_json}

How to work:
- For ANY application/API (payments, CRM, email providers, issue trackers, cloud, internal tools, etc.):
  if a matching tool is in the catalog, call `call_external_tool` with its agent_tool_name and JSON arguments.
  If it is missing, call `build_integration` with the app's OpenAPI URL, API docs URL, a website URL, or a precise description.
  Websites with no OpenAPI still get catalog tools (browser tools). HTTP APIs get REST tools. Then use them.
  Pass `api_credential_name` when the user has stored an API key (check `list_stored_credentials` first).
- For work inside a website: prefer catalog tools for that site (`call_external_tool`), or `browse_website`.
  Pass a stored credential name for logins. Never ask the user to paste passwords into chat.
- Build a landing page or a medium/large website or app as files: `generate_project` (use scale full for multi-page/apps).
- Email is one outbound action: `send_email` (needs a stored "smtp" credential). Prefer an app's own API
  via build_integration + call_external_tool when that is what the user asked for. Do not stop at drafting mail
  when the user asked to browse a site, build an app, or call APIs.
- Resumes: `create_resume` from free text; `analyze_resume_ats` / `tailor_resume` when structured JSON already exists.
- Long-term context: `search_memory` / `store_memory`.
Do not guess private URLs. If a tool fails, the workflow engine handles retries.

Workflow History Context:
{workflow_context}
"""
    
    agent_tools = [
        call_external_tool, build_integration, browse_website, send_email,
        list_stored_credentials, check_website_health, debug_code, generate_project,
        create_resume, analyze_resume_ats, tailor_resume,
    ]
    if memory_repo and embedding_service:
        agent_tools.extend([search_memory, store_memory])
        
    return LlmAgent(
        name="OrchestratorAgent",
        instruction=instruction,
        model=llm,
        tools=agent_tools
    )
