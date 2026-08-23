from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uuid
import logging
import asyncio
import json
from backend.models.schemas import WorkflowRun, Task, TaskStatus, WorkflowDefinition
from backend.repositories.firestore_workflow_repository import FirestoreWorkflowRepository
from backend.repositories.in_memory_message_bus import InMemoryMessageBus
from backend.agents.intent.intent_agent import get_intent_agent
from backend.agents.planner.planner_agent import get_planner_agent
from backend.engine.dag_validator import validate_dag, DAGValidationError
from backend.engine.engine import WorkflowEngine
from backend.config.settings import settings
from backend.api.dependencies.auth import get_current_user
from google.adk.runners import InMemoryRunner
import traceback

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.APP_NAME, version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Application state
workflow_repo = None
message_bus = None
workflow_engine = None

@app.on_event("startup")
async def startup_event():
    global workflow_repo, message_bus, workflow_engine
    logger.info(f"Starting {settings.APP_NAME} in {settings.APP_ENV} environment.")
    logger.info(f"Gemini Model: {settings.GEMINI_MODEL}")
    logger.info(f"Google Cloud Project: {settings.GOOGLE_CLOUD_PROJECT}")
    try:
        workflow_repo = FirestoreWorkflowRepository()
        logger.info("Firestore configured: YES")
    except Exception as e:
        logger.error(f"Firestore configured: NO - {e}")
        # Intentionally bubble up the error to fail fast if ADC is invalid
        raise e
        
    # We use InMemoryMessageBus for local development and deterministic tests as per the design
    # A real deployment would configure PubSubMessageBus
    message_bus = InMemoryMessageBus()
    from backend.instrumentation.wrappers import InstrumentedWorkflowEngine
    workflow_engine = InstrumentedWorkflowEngine(WorkflowEngine(workflow_repo, message_bus))
    
    # In a real deployed app, the worker would be a separate process.
    # For Phase 2 local development simplicity with InMemoryMessageBus, we can start a background consumer
    from backend.worker import start_worker
    import asyncio
    asyncio.create_task(start_worker(message_bus, workflow_engine))
    
    logger.info("API configuration valid: YES")

class GoalRequest(BaseModel):
    goal: str

@app.post("/api/v1/intent")
async def process_goal(request: GoalRequest):
    if not workflow_repo:
        raise HTTPException(status_code=500, detail="Database not initialized")
        
    run_id = str(uuid.uuid4())
    workflow_id = "default_workflow"
    
    try:
        # 1. Intent
        intent_agent = get_intent_agent()
        intent_runner = InMemoryRunner(agent=intent_agent, app_name=settings.APP_NAME)
        intent_events = await intent_runner.run_debug(request.goal)
        intent_output = intent_events[-1].output
        intent_result = intent_output.model_dump() if hasattr(intent_output, 'model_dump') else {"result": str(intent_output)}
        
        # 2. Plan (Produces WorkflowDefinition)
        planner_agent = get_planner_agent()
        planner_runner = InMemoryRunner(agent=planner_agent, app_name=settings.APP_NAME)
        plan_events = await planner_runner.run_debug(str(intent_result))
        plan_output = plan_events[-1].output
        
        # Parse output as WorkflowDefinition
        if hasattr(plan_output, 'model_dump'):
            workflow_def = WorkflowDefinition(**plan_output.model_dump())
        else:
            raise Exception("Planner did not return a valid WorkflowDefinition")
            
        # 3. Validate DAG
        validate_dag(workflow_def)
        
        # 4. Save to Firestore
        run = WorkflowRun(run_id=run_id, workflow_id=workflow_id, goal=request.goal, status=TaskStatus.RUNNING)
        for t_def in workflow_def.tasks:
            task = Task(
                task_id=t_def.task_id,
                workflow_id=workflow_id,
                run_id=run_id,
                agent=t_def.agent,
                tool=t_def.tool,
                input_data=t_def.input_data,
                dependencies=t_def.dependencies,
                timeout_seconds=t_def.timeout_seconds,
                max_retries=t_def.max_retries,
                status=TaskStatus.PENDING
            )
            run.tasks.append(task)
            
        workflow_repo.save_run(run)
        
        # Emit WORKFLOW_STARTED
        from backend.models.schemas import WorkflowEvent, WorkflowEventType
        start_event = WorkflowEvent(
            type=WorkflowEventType.WORKFLOW_STARTED,
            workflow_id=workflow_id,
            run_id=run_id,
            summary=f"Workflow started for goal: {request.goal}"
        )
        workflow_repo.save_event(start_event)
        
        # 5. Evaluate DAG to trigger root tasks
        await workflow_engine.evaluate_dag(run_id)
        
        return {"run_id": run_id, "status": run.status, "message": "Workflow created and executing."}
        
    except DAGValidationError as e:
        logger.error(f"DAG Validation failed: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid Plan: {e}")
    except Exception as e:
        traceback.print_exc()
        logger.error(f"Execution failed: {e}")
        # Run might not exist yet if it failed before saving, but we can't save it without a full DAG usually.
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/workflows/{run_id}")
async def get_workflow(run_id: str, user_id: str = Depends(get_current_user)):
    if not workflow_repo:
        raise HTTPException(status_code=500, detail="Database not initialized")
    run = workflow_repo.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if run.user_id != user_id and run.user_id != "default_user":
        raise HTTPException(status_code=403, detail="Access denied")
    return run

@app.get("/api/v1/workflows/{run_id}/events")
async def stream_workflow_events(run_id: str, request: Request, user_id: str = Depends(get_current_user)):
    if not workflow_repo:
        raise HTTPException(status_code=500, detail="Database not initialized")
    run = workflow_repo.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if run.user_id != user_id and run.user_id != "default_user":
        raise HTTPException(status_code=403, detail="Access denied")

    async def event_generator():
        try:
            async for event in workflow_repo.stream_events(run_id):
                if await request.is_disconnected():
                    break
                yield f"data: {event.model_dump_json()}\n\n"
        except Exception as e:
            logger.error(f"SSE stream error: {e}")
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")
