import os
import json
import logging
import asyncio
from datetime import datetime, timezone
from typing import Optional
import importlib.util
import ast

logger = logging.getLogger(__name__)

class CodeGenerator:
    """
    Generates deterministic, safe MCP server Python code using the LLM.
    Ensures credentials are via reference and safety rules are applied.
    """
    
    def __init__(self, llm_client):
        self.llm = llm_client

    async def generate_mcp_server(self, name: str, source_material: str, method: str) -> str:
        """
        Generates Python code for an MCP server given OpenAPI specs or descriptions.
        """
        logger.info(f"Generating MCP server '{name}' from {method}...")
        
        prompt = f"""
You are an expert Python engineer building a Model Context Protocol (MCP) server.
Your task is to write a complete, standalone Python script that implements an MCP server using the 'mcp' SDK.

Target API / Description:
{source_material}

Integration Name: {name}

RULES:
1. Use the FastMCP framework from the 'mcp' package (e.g. from mcp.server.fastmcp import FastMCP).
2. The server must be named "{name.replace(' ', '_')}_MCP".
3. Write fully typed functions decorated with @mcp.tool().
4. DO NOT hardcode ANY API keys, secrets, or bearer tokens. All credentials must be read from environment variables (e.g., os.environ.get('API_KEY')).
5. Use 'httpx' or 'aiohttp' for network requests. Do not use 'requests' as it blocks asyncio.
6. Return ONLY the raw Python code. No markdown code blocks, no explanations, no HTML.
7. ABSOLUTELY NO eval(), exec(), subprocess, or os.system() calls.
8. Catch exceptions and return graceful string error messages. Do not crash the server.

Generate the complete Python script now:
"""
        response = await self.llm.generate(prompt)
        code = response.text.strip()
        
        if code.startswith("```python"):
            code = code[9:]
        if code.startswith("```"):
            code = code[3:]
        if code.endswith("```"):
            code = code[:-3]
            
        return code.strip()

    def static_security_check(self, code: str) -> bool:
        """
        Stage B: Fast AST scan for dangerous calls.
        """
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        if node.func.id in ['eval', 'exec', 'open']:
                            logger.error(f"Security check failed: {node.func.id}() is not allowed.")
                            return False
                    if isinstance(node.func, ast.Attribute):
                        if node.func.attr in ['system', 'popen', 'run']:
                            logger.error(f"Security check failed: dangerous attribute access {node.func.attr}.")
                            return False
                if isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
                    module = getattr(node, 'module', None) or (node.names[0].name if hasattr(node, 'names') else None)
                    if module in ['subprocess', 'pty', 'os.system']:
                        logger.error(f"Security check failed: importing {module} is not allowed.")
                        return False
            return True
        except Exception as e:
            logger.error(f"Failed to parse AST for security check: {e}")
            return False
