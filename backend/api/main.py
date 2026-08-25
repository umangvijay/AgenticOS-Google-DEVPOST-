"""
AgentOS — API Entry Point (PRODUCTION)

FastAPI application with:
- Repository Factory initialization (SQLite or Firestore)
- JWT + Security initialization
- Auth router (signup, login, Google OAuth, refresh, logout)
- Workflow router (intent → plan → execute)
- SSE event streaming
- CSRF middleware
- Security headers
"""

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
import uuid
import logging
import asyncio
import json
import traceback

from backend.config.settings import settings
from backend.api.dependencies.auth import get_current_user, AuthenticatedUser
from backend.security.input_sanitizer import sanitize_goal, InputValidationError
from backend.security.rate_limiter import check_rate_limit
from backend.security.csrf import validate_csrf, set_csrf_cookie

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════
#  APPLICATION
# ══════════════════════════════════════════════════════════════════

app = FastAPI(
    title=settings.APP_NAME,
    version="2.0.0",
    description="The autonomous workspace that builds its own tools.",
    docs_url="/api/docs" if settings.APP_ENV == "development" else None,
    redoc_url="/api/redoc" if settings.APP_ENV == "development" else None,
)

# ── CORS ──────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[
        "X-RateLimit-Limit", "X-RateLimit-Remaining",
        "X-RateLimit-Reset", "Retry-After",
    ],
)

# ── Routers ───────────────────────────────────────────────────────
from backend.api.routers import approvals
from backend.api.routers.auth import router as auth_router
from backend.api.routers.workflows import router as workflows_router
from backend.api.routers.integrations import router as integrations_router
from backend.api.routers.notifications import router as notifications_router
from backend.api.routers.settings_router import router as settings_router
from backend.api.routers.schedules import router as schedules_router
from backend.api.routers.memory import router as memory_router
from backend.api.routers.resume import router as resume_router

app.include_router(auth_router, prefix="/api/v1")
app.include_router(workflows_router, prefix="/api/v1")
app.include_router(integrations_router, prefix="/api/v1")
app.include_router(notifications_router, prefix="/api/v1")
app.include_router(settings_router, prefix="/api/v1")
app.include_router(schedules_router, prefix="/api/v1")
app.include_router(memory_router, prefix="/api/v1")
app.include_router(resume_router, prefix="/api/v1")
app.include_router(approvals.router, prefix="/api/v1")



# ── Security Headers Middleware ───────────────────────────────────
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self';"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if settings.APP_ENV != "development":
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    return response


# ── CSRF Middleware ───────────────────────────────────────────────
@app.middleware("http")
async def csrf_middleware(request: Request, call_next):
    """Validate CSRF on state-changing requests."""
    try:
        validate_csrf(request)
    except HTTPException as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )
    response = await call_next(request)
    return response


# ══════════════════════════════════════════════════════════════════
#  STARTUP / SHUTDOWN
# ══════════════════════════════════════════════════════════════════

@app.on_event("startup")
async def startup_event():
    logger.info(f"Starting {settings.APP_NAME} v2.0.0 [{settings.APP_ENV}]")
    logger.info(f"Storage backend: {settings.STORAGE_BACKEND}")
    logger.info(f"Gemini model: {settings.GEMINI_MODEL}")

    # 1. Initialize Repository Factory
    from backend.repositories.factory import RepositoryFactory
    factory = RepositoryFactory()
    await factory.initialize()
    app.state.factory = factory

    # 2. Initialize JWT Manager (auto-generates RSA keys on first run)
    from backend.security.jwt_manager import jwt_manager
    jwt_manager.initialize()

    # 3. Initialize Secrets Vault (auto-generates master key on first run)
    from backend.security.secrets_vault import secrets_vault
    secrets_vault.initialize()

    # 4. Initialize ToolRouter and Approvals
    from backend.mcp.tool_router import ToolRouter
    from backend.mcp.tool_policy import ToolPolicy
    from backend.services.approvals_engine import ApprovalsEngine
    
    approvals_engine = ApprovalsEngine()
    tool_policy = ToolPolicy()
    tool_router = ToolRouter(factory.mcp_repo, tool_policy, approvals_engine, factory.idempotency_repo)
    
    app.state.tool_router = tool_router

    # 5. Initialize AgentFactory
    from backend.agents.agent_factory import AgentFactory
    from backend.services.runtime_snapshot import RuntimeSnapshotRegistry
    snapshot_registry = RuntimeSnapshotRegistry()
    agent_factory = AgentFactory(snapshot_registry, tool_router)
    app.state.agent_factory = agent_factory

    # 6. Initialize Workflow Engine
    from backend.engine.engine import WorkflowEngine
    from backend.instrumentation.wrappers import InstrumentedWorkflowEngine
    workflow_engine = InstrumentedWorkflowEngine(
        WorkflowEngine(factory.workflow_repo, factory.message_bus, agent_factory, factory.memory_repo)
    )
    app.state.workflow_engine = workflow_engine

    # 7. Start background worker
    from backend.worker import start_worker
    asyncio.create_task(start_worker(factory.message_bus, workflow_engine))

    logger.info("All systems initialized. Ready to serve requests.")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down...")
    factory = getattr(app.state, "factory", None)
    if factory:
        await factory.shutdown()
    logger.info("Shutdown complete.")


# ══════════════════════════════════════════════════════════════════
#  HEALTH CHECK
# ══════════════════════════════════════════════════════════════════

@app.get("/health")
async def health_check():
    factory = getattr(app.state, "factory", None)
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": "2.0.0",
        "storage": settings.STORAGE_BACKEND,
        "model": settings.GEMINI_MODEL,
        "factory_initialized": factory is not None and factory._initialized,
    }


@app.get("/api/v1/csrf-token")
async def get_csrf_token(request: Request):
    """Get a CSRF token. Frontend calls this on page load."""
    from fastapi.responses import JSONResponse
    token = None
    response = JSONResponse({"csrf_token": "set_in_cookie"})
    token = set_csrf_cookie(response)
    return JSONResponse(
        {"csrf_token": token},
        headers=dict(response.headers),
    )


# ══════════════════════════════════════════════════════════════════
#  INTENT → PLAN → EXECUTE (Main workflow endpoint)
# ══════════════════════════════════════════════════════════════════

class GoalRequest(BaseModel):
    goal: str


@app.post("/api/v1/intent")
async def process_goal(
    body: GoalRequest,
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Process a user's goal through the intent → plan → execute pipeline.
    Real-time AI processing: no hardcoded responses.
    """
    factory = getattr(request.app.state, "factory", None)
    workflow_engine = getattr(request.app.state, "workflow_engine", None)
    if not factory or not workflow_engine:
        raise HTTPException(status_code=500, detail="Server not initialized")

    # Rate limit
    check_rate_limit(f"user:{user.user_id}", "workflow")

    # Sanitize the goal
    try:
        goal = sanitize_goal(body.goal)
    except InputValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)

    if not goal:
        raise HTTPException(status_code=400, detail="Goal cannot be empty")

    run_id = str(uuid.uuid4())
    workflow_id = f"wf-{run_id[:8]}"

    try:
        from backend.models.schemas import (
            WorkflowRun, Task, TaskStatus, WorkflowDefinition,
            WorkflowEvent, WorkflowEventType,
        )
        from backend.agents.intent.intent_agent import get_intent_agent
        from backend.agents.planner.planner_agent import get_planner_agent
        from backend.engine.dag_validator import validate_dag, DAGValidationError
        from google.adk.runners import InMemoryRunner
        from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

        # Wrap runner execution with retries to handle 503 Overloaded errors
        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            reraise=True
        )
        async def run_with_retries(runner, input_data):
            return await runner.run_debug(input_data)


        # Helper: extract text from ADK Event
        def extract_event_text(events):
            for event in reversed(events):
                if event.output is not None:
                    if hasattr(event.output, 'model_dump'):
                        return event.output.model_dump()
                    return event.output
                if hasattr(event, 'content') and event.content and hasattr(event.content, 'parts'):
                    for part in event.content.parts:
                        if hasattr(part, 'text') and part.text:
                            return part.text
            return None

        # 1. Intent — real-time AI analysis of the user's goal
        intent_agent = get_intent_agent()
        intent_runner = InMemoryRunner(agent=intent_agent, app_name=settings.APP_NAME)
        intent_events = await run_with_retries(intent_runner, goal)
        raw_intent = extract_event_text(intent_events)

        if isinstance(raw_intent, dict):
            intent_result = raw_intent
        elif isinstance(raw_intent, str):
            intent_result = json.loads(raw_intent)
        else:
            intent_result = {"action": "unknown", "target": goal}

        logger.info(f"[{run_id[:8]}] Intent: {intent_result}")

        # 2. Plan — real-time workflow planning by AI
        planner_agent = get_planner_agent()
        planner_runner = InMemoryRunner(agent=planner_agent, app_name=settings.APP_NAME)
        plan_events = await run_with_retries(planner_runner, json.dumps(intent_result))
        raw_plan = extract_event_text(plan_events)

        if isinstance(raw_plan, dict):
            workflow_def = WorkflowDefinition(**raw_plan)
        elif isinstance(raw_plan, str):
            workflow_def = WorkflowDefinition(**json.loads(raw_plan))
        else:
            raise Exception(f"Planner returned unexpected output type: {type(raw_plan)}")

        logger.info(f"[{run_id[:8]}] DAG: {len(workflow_def.tasks)} tasks")

        # 3. Validate DAG
        validate_dag(workflow_def)

        # 4. Create WorkflowRun with real user identity
        run = WorkflowRun(
            run_id=run_id,
            workflow_id=workflow_id,
            user_id=user.user_id,  # Real authenticated user
            goal=goal,
            status=TaskStatus.RUNNING,
        )
        for t_def in workflow_def.tasks:
            task = Task(
                task_id=t_def.task_id,
                workflow_id=workflow_id,
                run_id=run_id,
                user_id=user.user_id,  # Real authenticated user
                agent=t_def.agent,
                tool=t_def.tool,
                input_data=t_def.input_data,
                dependencies=t_def.dependencies,
                timeout_seconds=t_def.timeout_seconds,
                max_retries=t_def.max_retries,
                status=TaskStatus.PENDING,
            )
            run.tasks.append(task)

        # Save to repository (SQLite or Firestore, based on config)
        run_dict = run.model_dump(mode="json")
        tasks_dicts = [t.model_dump(mode="json") for t in run.tasks]
        run_dict["tasks"] = tasks_dicts
        await factory.workflow_repo.save_run(run_dict)

        # Emit WORKFLOW_STARTED event
        start_event = WorkflowEvent(
            type=WorkflowEventType.WORKFLOW_STARTED,
            workflow_id=workflow_id,
            run_id=run_id,
            summary=f"Workflow started for goal: {goal}",
        )
        await factory.workflow_repo.save_event(start_event.model_dump(mode="json"))

        # Audit log
        await factory.audit_repo.log_event({
            "event_type": "WORKFLOW_CREATED",
            "actor_id": user.user_id,
            "actor_type": "USER",
            "resource_id": run_id,
            "workflow_id": workflow_id,
            "run_id": run_id,
            "details": {"goal": goal, "task_count": len(workflow_def.tasks)},
        })

        # 5. Evaluate DAG to trigger root tasks
        await workflow_engine.evaluate_dag(run_id)

        return {
            "run_id": run_id,
            "workflow_id": workflow_id,
            "status": run.status,
            "task_count": len(run.tasks),
            "message": "Workflow created and executing.",
        }

    except DAGValidationError as e:
        logger.error(f"DAG Validation failed: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid Plan: {e}")
    except Exception as e:
        traceback.print_exc()
        logger.error(f"Execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════════
#  WORKFLOW ENDPOINTS
# ══════════════════════════════════════════════════════════════════

@app.get("/api/v1/workflows")
async def list_workflows(
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    limit: int = 50,
    offset: int = 0,
):
    """List the authenticated user's workflow runs."""
    factory = getattr(request.app.state, "factory", None)
    if not factory:
        raise HTTPException(status_code=500, detail="Server not initialized")

    runs = await factory.workflow_repo.list_runs(user.user_id, limit=limit, offset=offset)
    return {"workflows": runs, "count": len(runs)}


@app.get("/api/v1/workflows/{run_id}")
async def get_workflow(
    run_id: str,
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Get a specific workflow run with all its tasks."""
    factory = getattr(request.app.state, "factory", None)
    if not factory:
        raise HTTPException(status_code=500, detail="Server not initialized")

    run = await factory.workflow_repo.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Resource-level access control — users can only see their own workflows
    if run.get("user_id") != user.user_id and not user.is_admin():
        raise HTTPException(status_code=403, detail="Access denied")

    return run


@app.get("/api/v1/workflows/{run_id}/events")
async def stream_workflow_events(
    run_id: str,
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Stream workflow events via SSE."""
    factory = getattr(request.app.state, "factory", None)
    if not factory:
        raise HTTPException(status_code=500, detail="Server not initialized")

    run = await factory.workflow_repo.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if run.get("user_id") != user.user_id and not user.is_admin():
        raise HTTPException(status_code=403, detail="Access denied")

    async def event_generator():
        """Poll-based SSE for SQLite mode."""
        last_event_id = None
        while True:
            if await request.is_disconnected():
                break
            events = await factory.workflow_repo.get_events(run_id, after_event_id=last_event_id)
            for event in events:
                last_event_id = event["event_id"]
                yield f"id: {event['event_id']}\ndata: {json.dumps(event)}\n\n"
            await asyncio.sleep(1)  # Poll interval

    return StreamingResponse(event_generator(), media_type="text/event-stream")
