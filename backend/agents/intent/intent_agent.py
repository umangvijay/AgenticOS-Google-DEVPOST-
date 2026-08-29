from google.adk.agents.llm_agent import LlmAgent
from google.adk.models.google_llm import Gemini
from backend.services.llm_context import gemini_adk_kwargs
from backend.config.settings import settings
from backend.models.schemas import IntentSchema

def get_intent_agent() -> LlmAgent:
    llm = Gemini(
        model=settings.GEMINI_MODEL,
        client_kwargs=gemini_adk_kwargs(),
    )
    
    return LlmAgent(
        name="IntentAgent",
        instruction="Extract the core intent and parameters from the following user goal.",
        model=llm,
        output_schema=IntentSchema
    )
