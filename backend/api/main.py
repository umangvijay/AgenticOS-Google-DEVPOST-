from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid
import logging
from backend.models.schemas import WorkflowRun, Task, TaskStatus
from backend.repositories.firestore_workflow_repository import FirestoreWorkflowRepository
from backend.agents.intent.intent_agent import get_intent_agent
from backend.agents.planner.planner_agent import get_planner_agent
from backend.agents.orchestrator.orchestrator_agent import get_orchestrator_agent
from backend.config.settings import settings
from google.adk.runners import InMemoryRunner

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.APP_NAME, version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Application state
workflow_repo = None

@app.on_event("startup")
async def startup_event():
    global workflow_repo
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
    logger.info("API configuration valid: YES")

class GoalRequest(BaseModel):
    goal: str

@app.post("/api/v1/intent")
async def process_goal(request: GoalRequest):
    if not workflow_repo:
        raise HTTPException(status_code=500, detail="Database not initialized")
        
    run_id = str(uuid.uuid4())
    run = WorkflowRun(run_id=run_id, goal=request.goal, status=TaskStatus.RUNNING)
    workflow_repo.save_run(run)
    
    try:
        # 1. Intent
        intent_agent = get_intent_agent()
        intent_runner = InMemoryRunner(agent=intent_agent, app_name=settings.APP_NAME)
        intent_events = await intent_runner.run_debug(request.goal)
        intent_output = intent_events[-1].output
        intent_result = intent_output.model_dump() if hasattr(intent_output, 'model_dump') else {"result": str(intent_output)}
        
        run.tasks.append(Task(task_id=str(uuid.uuid4()), workflow_id=run_id, name="Parse Intent", agent="IntentAgent", status=TaskStatus.COMPLETED, output_data=intent_result))
        workflow_repo.save_run(run)
        
        # 2. Plan
        planner_agent = get_planner_agent()
        planner_runner = InMemoryRunner(agent=planner_agent, app_name=settings.APP_NAME)
        plan_events = await planner_runner.run_debug(str(intent_result))
        plan_output = plan_events[-1].output
        plan_result = plan_output.model_dump() if hasattr(plan_output, 'model_dump') else {"result": str(plan_output)}
        
        run.tasks.append(Task(task_id=str(uuid.uuid4()), workflow_id=run_id, name="Create Plan", agent="PlannerAgent", status=TaskStatus.COMPLETED, output_data=plan_result))
        workflow_repo.save_run(run)
        
        # 3. Orchestrate
        orch_agent = get_orchestrator_agent()
        orch_runner = InMemoryRunner(agent=orch_agent, app_name=settings.APP_NAME)
        orch_events = await orch_runner.run_debug(f"Execute this plan step by step: {str(plan_result)}")
        orch_result = str(orch_events[-1].output) if orch_events else ""
        
        run.tasks.append(Task(task_id=str(uuid.uuid4()), workflow_id=run_id, name="Execute Tools", agent="OrchestratorAgent", status=TaskStatus.COMPLETED, output_data={"result": orch_result}))
        
        run.status = TaskStatus.COMPLETED
        workflow_repo.save_run(run)
        
        return {"run_id": run_id, "status": run.status, "result": orch_result}
    except Exception as e:
        logger.error(f"Execution failed: {e}")
        run.status = TaskStatus.FAILED
        workflow_repo.save_run(run)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/workflows/{run_id}")
async def get_workflow(run_id: str):
    if not workflow_repo:
        raise HTTPException(status_code=500, detail="Database not initialized")
    run = workflow_repo.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return run
