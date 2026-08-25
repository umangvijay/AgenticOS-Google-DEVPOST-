from google.adk.agents.llm_agent import LlmAgent
from google.adk.models.google_llm import Gemini
from backend.config.settings import settings
from backend.models.schemas import IntentSchema

def get_intent_agent() -> LlmAgent:
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
        name="IntentAgent",
        instruction="Extract the core intent and parameters from the following user goal.",
        model=llm,
        output_schema=IntentSchema
    )
