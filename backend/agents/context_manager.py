"""
AgentOS — LLM Context Window Manager

Prevents context overflow during long-running workflows.
Sliding window + periodic summarization.

- Last N tasks (default: 5) included in full
- Older tasks summarized into a concise paragraph
- Per-user daily token budget enforcement
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, date

from backend.config.settings import settings

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────
DEFAULT_WINDOW_SIZE = 5          # Number of recent tasks to include in full
TOKEN_WARN_THRESHOLD = 0.8      # Warn at 80% usage
CHARS_PER_TOKEN = 4              # Rough estimate for Gemini tokenizer
MAX_CONTEXT_TOKENS = 30_000      # Trigger summarization above this


class ContextManager:
    """
    Manages the context window for agent prompts.
    
    Usage:
        ctx = ContextManager()
        
        # Build context for an agent from workflow history
        prompt_context = ctx.build_context(tasks, window_size=5)
        
        # Track token usage
        ctx.record_usage(user_id, input_tokens, output_tokens)
        budget = ctx.check_budget(user_id)
    """

    def __init__(self):
        # In-memory token usage tracking (per user per day)
        # In production, this would be in the database
        self._usage: Dict[str, Dict[str, int]] = {}

    def build_context(
        self,
        tasks: List[Dict[str, Any]],
        window_size: int = DEFAULT_WINDOW_SIZE,
        include_summary: bool = True,
    ) -> Dict[str, Any]:
        """
        Build a context window from workflow tasks.
        
        Returns:
            {
                "recent_tasks": [...],      # Last N tasks in full detail
                "older_summary": "...",     # Summary of older tasks
                "total_tasks": int,
                "context_tokens_estimate": int,
            }
        """
        if not tasks:
            return {
                "recent_tasks": [],
                "older_summary": "",
                "total_tasks": 0,
                "context_tokens_estimate": 0,
            }

        # Split into recent and older
        recent = tasks[-window_size:]
        older = tasks[:-window_size] if len(tasks) > window_size else []

        # Build recent task details
        recent_details = []
        for task in recent:
            detail = {
                "task_id": task.get("task_id", ""),
                "agent": task.get("agent", ""),
                "tool": task.get("tool"),
                "status": task.get("status", ""),
                "input_summary": self._summarize_data(task.get("input_data", {})),
                "output_summary": self._summarize_data(task.get("output_data")),
                "error": task.get("error"),
            }
            recent_details.append(detail)

        # Summarize older tasks
        older_summary = ""
        if older and include_summary:
            older_summary = self._create_task_summary(older)

        # Estimate token count
        import json
        context_str = json.dumps(recent_details) + older_summary
        token_estimate = len(context_str) // CHARS_PER_TOKEN

        return {
            "recent_tasks": recent_details,
            "older_summary": older_summary,
            "total_tasks": len(tasks),
            "context_tokens_estimate": token_estimate,
        }

    def needs_summarization(self, tasks: List[Dict[str, Any]]) -> bool:
        """Check if the context needs summarization based on estimated tokens."""
        import json
        total_chars = sum(
            len(json.dumps(t.get("input_data", {}))) +
            len(json.dumps(t.get("output_data") or {})) +
            len(t.get("error", "") or "")
            for t in tasks
        )
        return (total_chars // CHARS_PER_TOKEN) > MAX_CONTEXT_TOKENS

    # ── Token Budget ──────────────────────────────────────────────

    def record_usage(
        self, user_id: str, input_tokens: int, output_tokens: int
    ) -> None:
        """Record token usage for a user."""
        today = date.today().isoformat()
        key = f"{user_id}:{today}"

        if key not in self._usage:
            self._usage[key] = {"input": 0, "output": 0, "total": 0}

        self._usage[key]["input"] += input_tokens
        self._usage[key]["output"] += output_tokens
        self._usage[key]["total"] += input_tokens + output_tokens

    def check_budget(self, user_id: str, daily_limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Check token budget for a user.
        
        Returns:
            {
                "used": int,
                "limit": int,
                "remaining": int,
                "percentage": float,
                "exceeded": bool,
                "warning": bool,
            }
        """
        limit = daily_limit or settings.DEFAULT_DAILY_TOKEN_LIMIT
        today = date.today().isoformat()
        key = f"{user_id}:{today}"

        usage = self._usage.get(key, {"total": 0})
        used = usage["total"]
        remaining = max(0, limit - used)
        pct = (used / limit * 100) if limit > 0 else 100

        return {
            "used": used,
            "limit": limit,
            "remaining": remaining,
            "percentage": round(pct, 1),
            "exceeded": used >= limit,
            "warning": pct >= (TOKEN_WARN_THRESHOLD * 100),
        }

    def get_usage_breakdown(self, user_id: str) -> Dict[str, int]:
        """Get detailed usage breakdown for today."""
        today = date.today().isoformat()
        key = f"{user_id}:{today}"
        return dict(self._usage.get(key, {"input": 0, "output": 0, "total": 0}))

    # ── Private Helpers ───────────────────────────────────────────

    @staticmethod
    def _summarize_data(data: Any, max_length: int = 200) -> str:
        """Create a brief summary of task data."""
        if data is None:
            return ""
        if isinstance(data, str):
            return data[:max_length] + ("..." if len(data) > max_length else "")
        if isinstance(data, dict):
            import json
            s = json.dumps(data)
            return s[:max_length] + ("..." if len(s) > max_length else "")
        return str(data)[:max_length]

    @staticmethod
    def _create_task_summary(tasks: List[Dict[str, Any]]) -> str:
        """Create a human-readable summary of older tasks."""
        if not tasks:
            return ""

        completed = sum(1 for t in tasks if t.get("status") == "COMPLETED")
        failed = sum(1 for t in tasks if t.get("status") == "FAILED")
        other = len(tasks) - completed - failed

        agents = set(t.get("agent", "unknown") for t in tasks)
        tools = set(t.get("tool", "") for t in tasks if t.get("tool"))

        summary_parts = [
            f"Previously: {len(tasks)} tasks executed",
            f"({completed} completed, {failed} failed, {other} other).",
        ]

        if agents:
            summary_parts.append(f"Agents used: {', '.join(sorted(agents))}.")
        if tools:
            summary_parts.append(f"Tools used: {', '.join(sorted(tools))}.")

        # Include errors from failed tasks
        errors = [
            t.get("error", "")[:100]
            for t in tasks
            if t.get("status") == "FAILED" and t.get("error")
        ]
        if errors:
            summary_parts.append(f"Errors encountered: {'; '.join(errors[:3])}")

        return " ".join(summary_parts)


# ── Singleton ─────────────────────────────────────────────────────
context_manager = ContextManager()
