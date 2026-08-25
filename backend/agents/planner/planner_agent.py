from google.adk.agents.llm_agent import LlmAgent
from google.adk.models.google_llm import Gemini
from backend.config.settings import settings
from backend.models.schemas import WorkflowDefinition

def get_planner_agent() -> LlmAgent:
    client_kwargs = {}
    if not settings.GEMINI_API_KEY:
        client_kwargs = {
            "vertexai": True,
            "project": settings.GOOGLE_CLOUD_PROJECT,
            "location": settings.GOOGLE_CLOUD_REGION
        }
    else:
        client_kwargs = {"api_key": settings.GEMINI_API_KEY}
    
    llm = Gemini(
        model=settings.GEMINI_MODEL,
        client_kwargs=client_kwargs
    )
    
    return LlmAgent(
        name="PlannerAgent",
        instruction="Given an Intent, create a structured workflow definition DAG to execute it. Available tools: get_current_time.",
        model=llm,
        output_schema=WorkflowDefinition
    )
