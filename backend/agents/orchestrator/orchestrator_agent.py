import json
from google.adk.agents.llm_agent import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.tools.base_tool import adk_tool
from backend.config.settings import settings

def get_orchestrator_agent(tool_router=None, catalog_json: str = "[]") -> LlmAgent:
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
        model_name=settings.GEMINI_MODEL,
        client_kwargs=client_kwargs
    )
    
    @adk_tool
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
            result = await tool_router.execute_tool(agent_tool_name, args)
            return str(result)
        except Exception as e:
            # We return the error as a string so the LLM can see it and retry if needed
            # But the WorkflowEngine Phase 2 will also catch exceptions if they bubble up.
            # To bubble up retries/failures to Phase 2 workflow engine, we MUST raise it!
            raise e

    instruction = f"""You are the Orchestrator Agent. Your job is to execute the given task.
You have access to an external tool catalog:
{catalog_json}

To use a tool, call the `call_external_tool` function with the `agent_tool_name` and `arguments_json`.
Only use tools from the catalog. Do not attempt to guess URLs or use tools not in the catalog.
If a tool fails, it will raise an error which the workflow engine will handle (checkpoints, retries).
"""
    
    return LlmAgent(
        name="OrchestratorAgent",
        instruction=instruction,
        model=llm,
        tools=[call_external_tool]
    )
