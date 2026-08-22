from typing import Optional, List
from google.adk.agents.llm_agent import LlmAgent
from google.adk.models.google_llm import Gemini
from backend.config.settings import settings
from backend.models.plugin import PluginAgentDefinition
from backend.services.runtime_snapshot import RuntimeSnapshotRegistry
import json
import logging

logger = logging.getLogger(__name__)

class AgentFactory:
    def __init__(self, snapshot_registry: RuntimeSnapshotRegistry, tool_router):
        self.snapshot_registry = snapshot_registry
        self.tool_router = tool_router

    def build_agent(self, agent_id: str, context: Optional[dict] = None) -> Optional[LlmAgent]:
        """
        Dynamically constructs an ADK LlmAgent based on the active runtime snapshot.
        """
        snapshot = self.snapshot_registry.get_snapshot()
        definitions = snapshot.get_plugin_agent_definitions()
        
        agent_def = next((a for a in definitions if a.agent_id == agent_id), None)
        
        if not agent_def:
            logger.warning(f"Agent {agent_id} not found in current snapshot v{snapshot.version}")
            return None
            
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
        
        # We need to build the tool functions that delegate to ToolRouter
        agent_tools = []
        if self.tool_router and agent_def.allowed_tools:
            async def call_plugin_tool(agent_tool_name: str, arguments_json: str) -> str:
                if agent_tool_name not in agent_def.allowed_tools:
                    return f"Error: Tool {agent_tool_name} is not allowed for this agent."
                try:
                    args = json.loads(arguments_json)
                    result = await self.tool_router.execute_tool(agent_tool_name, args, context=context)
                    return str(result)
                except Exception as e:
                    raise e
            
            call_plugin_tool.__name__ = "call_plugin_tool"
            call_plugin_tool.__doc__ = f"Call an allowed plugin tool. Allowed tools: {', '.join(agent_def.allowed_tools)}"
            agent_tools.append(call_plugin_tool)
            
        return LlmAgent(
            name=agent_def.display_name,
            instruction=agent_def.instructions,
            model=llm,
            tools=agent_tools
        )
