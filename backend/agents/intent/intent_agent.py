from typing import Optional
from google.adk.agents.llm_agent import LlmAgent
from backend.services.llm_context import adk_gemini
from backend.services.gemini_client import candidate_models
from backend.models.schemas import IntentSchema

def get_intent_agent(model: Optional[str] = None) -> LlmAgent:
    llm = adk_gemini(candidate_models(model)[0])
    
    return LlmAgent(
        name="IntentAgent",
        instruction="Extract the core intent and parameters from the following user goal.",
        model=llm,
        output_schema=IntentSchema
    )
