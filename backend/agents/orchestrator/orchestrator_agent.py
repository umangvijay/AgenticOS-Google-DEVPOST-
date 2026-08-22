from google.adk.agents.llm_agent import LlmAgent
from google.adk.models.google_llm import Gemini
from backend.config.settings import settings
from backend.tools.time_tool import get_current_time

def get_orchestrator_agent() -> LlmAgent:
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
        name=settings.GEMINI_MODEL,
        client_kwargs=client_kwargs
    )
    
    return LlmAgent(
        name="OrchestratorAgent",
        instruction="Execute the given plan step by step using the provided tools. Output a summary of the result.",
        model=llm,
        tools=[get_current_time]
    )
