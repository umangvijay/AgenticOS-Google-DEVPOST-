import logging
from typing import Optional
from google.adk.agents.llm_agent import LlmAgent
from backend.services.llm_context import adk_gemini
from backend.models.recovery import RecoveryAction

logger = logging.getLogger(__name__)

def get_recovery_agent(model: Optional[str] = None) -> LlmAgent:
    llm = adk_gemini(model)
    
    instruction = """
    You are the AgenticOS RecoveryAgent.
    Your sole purpose is to analyze a semantic failure from a task and provide a strictly formatted recovery action.
    
    You will be provided with a RecoveryContext that includes:
    - The original input parameters
    - The most recent input parameters
    - The validation error or tool failure reason
    - The required JSON schema for the tool
    
    Your goal is to repair the input parameters so that they pass validation.
    
    RULES:
    1. You MUST return a valid JSON object matching the RecoveryAction schema.
    2. Do NOT invent new fields. Use the allowed_tool_schema strictly.
    3. If the error is impossible to fix (e.g. missing required data that cannot be inferred), set action to 'ABORT'.
    4. If the error can be fixed (e.g. type cast, removing an invalid enum, fixing a typo), set action to 'REPAIR' and provide the 'corrected_input'.
    5. You must NOT attempt to execute tools yourself. You only provide the corrected parameters.
    """
    
    # We configure the LlmAgent to use response_model for structured output
    agent = LlmAgent(
        name="RecoveryAgent",
        instruction=instruction,
        model=llm,
        output_schema=RecoveryAction
    )
    
    return agent
