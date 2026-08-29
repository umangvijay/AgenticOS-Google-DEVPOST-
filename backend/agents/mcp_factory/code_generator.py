import ast
import logging

logger = logging.getLogger(__name__)

ALLOWED_IMPORTS = {
    "os", "json", "typing", "datetime", "httpx", "aiohttp", "mcp",
    "pydantic", "asyncio", "re", "urllib", "urllib.parse",
}


class CodeGenerator:
    def __init__(self, llm_client=None):
        self.llm = llm_client

    def static_security_check(self, code: str) -> bool:
        try:
            tree = ast.parse(code)
        except Exception as e:
            logger.error("Failed to parse AST: %s", e)
            return False
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in {"eval", "exec", "compile", "open"}:
                    logger.error("Security check failed: %s()", node.func.id)
                    return False
                if isinstance(node.func, ast.Attribute) and node.func.attr in {"system", "popen", "run"}:
                    logger.error("Security check failed: %s", node.func.attr)
                    return False
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0]
                    if root not in ALLOWED_IMPORTS:
                        logger.error("Import not allowed: %s", alias.name)
                        return False
            if isinstance(node, ast.ImportFrom):
                root = (node.module or "").split(".")[0]
                if root and root not in ALLOWED_IMPORTS:
                    logger.error("Import not allowed: %s", node.module)
                    return False
        return True
