import logging
from datetime import datetime, timezone

class SecurityAuditLogger:
    def __init__(self):
        self.logger = logging.getLogger("agentos.security.audit")
        self.logger.setLevel(logging.INFO)
        
        # In a real environment, this might write to Cloud Logging / Datadog
        # For Phase 5, we'll write to a local log file that we can inspect in tests
        handler = logging.FileHandler("sandbox_security_audit.log")
        formatter = logging.Formatter('%(asctime)s - SECURITY_EVENT - [%(levelname)s] - %(message)s')
        handler.setFormatter(formatter)
        if not self.logger.handlers:
            self.logger.addHandler(handler)

    def log_sandbox_execution(self, mcp_id: str, tool_name: str, docker_cmd: str):
        self.logger.info(f"SANDBOX_SPAWN | MCP={mcp_id} | TOOL={tool_name} | CMD={docker_cmd}")

    def log_sandbox_violation(self, mcp_id: str, reason: str, details: str = ""):
        self.logger.warning(f"SANDBOX_VIOLATION | MCP={mcp_id} | REASON={reason} | DETAILS={details}")

    def log_sandbox_timeout(self, mcp_id: str, timeout_sec: int):
        self.logger.warning(f"SANDBOX_TIMEOUT | MCP={mcp_id} | TIMEOUT={timeout_sec}s")

audit_logger = SecurityAuditLogger()
