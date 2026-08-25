import json
import logging
from typing import Dict, Any
import httpx

from google.adk.models.google_llm import Gemini
from backend.config.settings import settings
from backend.repositories.mcp_repository import MCPRepository
from backend.agents.mcp_factory.code_generator import CodeGenerator
from backend.agents.mcp_factory.sandbox_tester import SandboxTester
from backend.agents.mcp_factory.tool_registry_manager import ToolRegistryManager

logger = logging.getLogger(__name__)

class MCPFactoryAgent:
    """
    The MCP Factory Agent.
    Orchestrates building MCP integrations dynamically from URLs or Prompts.
    """
    def __init__(self, mcp_repo: MCPRepository):
        client_kwargs = {}
        if not settings.GEMINI_API_KEY:
            client_kwargs = {
                "vertexai": True,
                "project": settings.GOOGLE_CLOUD_PROJECT,
                "location": settings.GOOGLE_CLOUD_REGION
            }
        else:
            client_kwargs = {"api_key": settings.GEMINI_API_KEY}
        
        self.llm = Gemini(
            model=settings.GEMINI_MODEL,
            client_kwargs=client_kwargs
        )
        
        self.code_gen = CodeGenerator(self.llm)
        self.tester = SandboxTester(workspace_dir="data/sandbox")
        self.registry = ToolRegistryManager(mcp_repo)

    async def build_from_prompt(self, prompt: str, name: str = "Custom Integration") -> Dict[str, Any]:
        """
        Builds an integration from a natural language prompt.
        """
        logger.info(f"Building integration '{name}' from prompt...")
        return await self._build(name, prompt, method="prompt", trust_tier="pending_review")
        
    async def build_from_url(self, url: str, name: str = "API Integration") -> Dict[str, Any]:
        """
        Builds an integration from an API documentation URL or OpenAPI spec.
        Actually fetches the URL content so that no hardcoded inputs are used.
        """
        logger.info(f"Building integration '{name}' from URL: {url}...")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                content = response.text
                
                # Truncate if extremely large, Gemini has a large context window but let's be safe
                if len(content) > 200000:
                    content = content[:200000] + "\n... (truncated due to length)"
                    
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP Error fetching API documentation from {url}: {e.response.status_code}")
            return {"status": "error", "message": f"Failed to fetch API documentation. The URL returned a {e.response.status_code} error. Please check the URL and try again."}
        except Exception as e:
            logger.error(f"Failed to fetch API documentation from {url}: {e}")
            return {"status": "error", "message": f"Failed to fetch API documentation: {e}"}

        source_material = f"API Documentation URL: {url}\n\nCONTENT:\n{content}\n\nPlease build a comprehensive MCP server for this API based strictly on the provided content."
        
        return await self._build(name, source_material, method="url", trust_tier="pending_review")

    async def _build(self, name: str, source: str, method: str, trust_tier: str) -> Dict[str, Any]:
        # 1. Generate Code
        code = await self.code_gen.generate_mcp_server(name, source, method)
        if not code:
            return {"status": "error", "message": "Failed to generate code."}
            
        # 2. Static Security Check
        if not self.code_gen.static_security_check(code):
            return {"status": "error", "message": "Generated code failed static security analysis."}
            
        # 3. Sandbox Testing
        test_result = await self.tester.run_test(f"test_{name.replace(' ', '_')}", code)
        if test_result.get("status") != "success":
            return {"status": "error", "message": f"Sandbox test failed: {test_result.get('message')}"}
            
        tools_list = test_result.get("tools", [])
        if not tools_list:
             return {"status": "error", "message": "Sandbox test passed, but no tools were found in the generated MCP server."}
             
        # 4. Register
        mcp_id = await self.registry.register_mcp(name, f"Auto-generated from {method}", code, trust_tier, tools_list)
        
        return {
            "status": "success",
            "message": f"Integration generated successfully with {len(tools_list)} tools.",
            "mcp_id": mcp_id,
            "tools": tools_list
        }
