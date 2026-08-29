import asyncio
import httpx
import re
import json
import logging
import random
import traceback
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from opentelemetry import trace
from backend.observability.tracing import get_tracer
from backend.models.schemas import Task, TaskStatus, ErrorType, TaskTriggerEvent, WorkflowEvent, WorkflowEventType
from backend.repositories.workflow_repository import WorkflowRepository
from backend.repositories.message_bus import MessageBus
from backend.agents.orchestrator.orchestrator_agent import get_orchestrator_agent
from google.adk.runners import InMemoryRunner
from backend.config.settings import settings
from backend.agents.agent_factory import AgentFactory
from backend.services.runtime_snapshot import RuntimeSnapshotRegistry
from backend.services.approvals_engine import ApprovalRequiredException
from backend.models.schemas import TaskRecoveryEvent, SemanticErrorReason
from backend.models.exceptions import SemanticException
from backend.engine.repo_adapter import load_run, persist_task, persist_run, persist_event, maybe_await

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)

class WorkflowEngine:
    def __init__(self, workflow_repo: WorkflowRepository, message_bus: MessageBus, agent_factory: AgentFactory = None, memory_repo=None, settings_repo=None):
        self.repo = workflow_repo
        self.message_bus = message_bus
        self.agent_factory = agent_factory
        self.memory_repo = memory_repo
        self.settings_repo = settings_repo

    async def _call_matching_catalog_tool(self, run, catalog, tool_router, context) -> Optional[Dict[str, Any]]:
        """When the model cannot pick a tool, call the catalog tool that matches the goal."""
        if not tool_router or not catalog:
            return None
        from backend.engine.mcp_catalog import arguments_for_catalog_tool, pick_catalog_tool
        tool = pick_catalog_tool(str(run.goal or ""), catalog)
        if not tool:
            return None
        tool_name = tool.get("agent_tool_name") or tool.get("name")
        if not tool_name:
            return None
        args = arguments_for_catalog_tool(tool, str(run.goal or ""))
        try:
            return await tool_router.execute_tool_safe(tool_name, args, context=context)
        except Exception as te:
            return {"tool": tool_name, "error": str(te)}
        
    def _emit_event(self, event_type: str, run_id: str, workflow_id: str, task_id: Optional[str] = None, status: Optional[str] = None, summary: str = "", metadata: dict = None):
        if metadata is None:
            metadata = {}
        event = WorkflowEvent(
            type=event_type,
            workflow_id=workflow_id,
            run_id=run_id,
            task_id=task_id,
            status=status,
            summary=summary,
            sanitized_metadata=metadata
        )
        asyncio.create_task(persist_event(self.repo, event))

    async def evaluate_dag(self, run_id: str) -> None:
        """
        Evaluate the DAG for a given run and trigger ready tasks.
        A task is ready if its dependencies are COMPLETED.
        """
        run = await load_run(self.repo, run_id)
        if not run:
            logger.error(f"Run {run_id} not found during DAG evaluation")
            return
            
        if run.status == TaskStatus.CANCELLED:
            logger.info(f"Run {run_id} is cancelled. Skipping evaluation.")
            return

        completed_tasks = {t.task_id for t in run.tasks if t.status == TaskStatus.COMPLETED}
        failed_or_cancelled_tasks = {t.task_id for t in run.tasks if t.status in [TaskStatus.FAILED, TaskStatus.CANCELLED]}
        skipped_tasks = {t.task_id for t in run.tasks if t.status == TaskStatus.SKIPPED}
        
        all_completed = True
        
        for task in run.tasks:
            if task.status in [TaskStatus.PENDING, TaskStatus.WAITING]:
                # Check dependencies
                deps_met = True
                deps_failed = False
                deps_skipped = False
                for dep in task.dependencies:
                    if dep in failed_or_cancelled_tasks:
                        deps_failed = True
                        break
                    if dep in skipped_tasks:
                        deps_skipped = True
                        break
                    if dep not in completed_tasks:
                        deps_met = False
                        break
                        
                if deps_failed:
                    task.status = TaskStatus.BLOCKED
                    await persist_task(self.repo, run_id, task)
                    logger.info(f"Task {task.task_id} BLOCKED due to failed dependencies")
                elif deps_skipped:
                    task.status = TaskStatus.SKIPPED
                    await persist_task(self.repo, run_id, task)
                    logger.info(f"Task {task.task_id} SKIPPED due to skipped dependencies")
                elif deps_met:
                    if task.status == TaskStatus.WAITING:
                        task.status = TaskStatus.PENDING
                        await persist_task(self.repo, run_id, task)
                        
                    # Trigger the task
                    event = TaskTriggerEvent(
                        workflow_id=run.workflow_id,
                        run_id=run_id,
                        task_id=task.task_id
                    )
                    await self.message_bus.publish("agentos-workflow-events", event)
                    logger.info(f"Triggered task {task.task_id} for run {run_id}")
                    all_completed = False
                else:
                    if task.status == TaskStatus.PENDING:
                        task.status = TaskStatus.WAITING
                        await persist_task(self.repo, run_id, task)
                    all_completed = False
            elif task.status not in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED, TaskStatus.BLOCKED, TaskStatus.SKIPPED]:
                all_completed = False

        if all_completed and run.status not in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            any_failed = any(t.status in [TaskStatus.FAILED, TaskStatus.BLOCKED] for t in run.tasks)
            if any_failed:
                run.status = TaskStatus.FAILED
                self._emit_event(WorkflowEventType.WORKFLOW_FAILED, run_id, run.workflow_id, summary="Workflow failed")
            else:
                run.status = TaskStatus.COMPLETED
                self._emit_event(WorkflowEventType.WORKFLOW_COMPLETED, run_id, run.workflow_id, summary="Workflow completed")
            await persist_run(self.repo, run)
            logger.info(f"Run {run_id} marked as {run.status}")

    def _calculate_backoff(self, attempt: int) -> float:
        """Exponential backoff with jitter."""
        base_delay = 2.0
        max_delay = 60.0
        delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
        jitter = random.uniform(0, 0.1 * delay)
        return delay + jitter

    # ══════════════════════════════════════════════════════════════════
    #  TASK EXECUTION (Hybrid Engine)
    # ══════════════════════════════════════════════════════════════════

    async def execute_task(self, run_id: str, task_id: str) -> None:
        """Execute a task using either Core Nodes or AI Agents."""
        run = await load_run(self.repo, run_id)
        if not run:
            return
            
        task = next((t for t in run.tasks if t.task_id == task_id), None)
        if not task:
            return
            
        if run.status == TaskStatus.CANCELLED:
            task.status = TaskStatus.CANCELLED
            await persist_task(self.repo, run_id, task)
            return

        lease_seconds = max(task.timeout_seconds + 10, 60)
        if task.status == TaskStatus.RECOVERING:
            return
            
        claimed = await maybe_await(self.repo.claim_task(run_id, task_id, lease_seconds))
        if not claimed:
            logger.info(f"Task {task_id} already claimed or completed.")
            return

        run = await load_run(self.repo, run_id)
        task = next((t for t in run.tasks if t.task_id == task_id), None)
        
        self._emit_event(WorkflowEventType.TASK_STARTED, run_id, run.workflow_id, task_id, task.status, f"Task {task_id} started execution")
        
        try:
            with tracer.start_as_current_span(f"task:{task.task_id}") as span:
                span.set_attribute("workflow.id", run.workflow_id)
                span.set_attribute("task.agent", task.agent)
                span.set_attribute("task.tool", str(task.tool))

                secrets_repo = None
                if self.agent_factory and getattr(self.agent_factory, "tool_router", None):
                    secrets_repo = getattr(self.agent_factory.tool_router, "secrets_repo", None)
                if secrets_repo and run.user_id:
                    from backend.services.llm_context import load_user_llm_keys
                    await load_user_llm_keys(secrets_repo, run.user_id)

                # ── Step 1: Variable Interpolation ────────────────────
                interpolated_input = self._interpolate(task.input_data, run)
                
                # ── Step 2: Route to Core Node or AI Agent ────────────
                if task.agent.startswith("core."):
                    result = await asyncio.wait_for(
                        self._execute_core_node(task, interpolated_input, run),
                        timeout=task.timeout_seconds
                    )
                else:
                    result = await asyncio.wait_for(
                        self._execute_ai_agent(task, run, run_id, task_id, interpolated_input),
                        timeout=task.timeout_seconds
                    )

                span.set_attribute("task.status", "COMPLETED")
                
                task.status = TaskStatus.COMPLETED
                task.completed_at = datetime.now(timezone.utc)
                task.output_data = result if isinstance(result, dict) else {"result": result}
                await persist_task(self.repo, run_id, task)
                logger.info(f"Task {task_id} completed successfully.")
                self._emit_event(WorkflowEventType.TASK_COMPLETED, run_id, run.workflow_id, task_id, task.status, f"Task {task_id} completed", metadata={"output": task.output_data})
                
                await self.evaluate_dag(run_id)
            
        except ApprovalRequiredException as e:
            logger.info(f"Task {task_id} requires human approval: {e.pending_approval.approval_id}")
            task.status = TaskStatus.WAITING_APPROVAL
            args = getattr(e.pending_approval, "arguments", None) or {}
            challenge = args.get("_challenge_type") if isinstance(args, dict) else None
            if challenge:
                task.output_data = {
                    "challenge_type": challenge,
                    "challenge_url": args.get("_challenge_url"),
                    "message": str(e),
                    "approval_id": e.pending_approval.approval_id,
                }
            await persist_task(self.repo, run_id, task)
            try:
                await maybe_await(self.repo.save_approval(e.pending_approval.model_dump(mode="json")))
            except Exception:
                logger.exception("Failed to persist approval request")
            summary = str(e) if challenge else f"Task {task_id} requires approval"
            self._emit_event(
                WorkflowEventType.APPROVAL_REQUIRED, run_id, run.workflow_id, task_id, task.status, summary,
                metadata={
                    "approval_id": e.pending_approval.approval_id,
                    "challenge_type": challenge,
                    "challenge_url": args.get("_challenge_url") if isinstance(args, dict) else None,
                },
            )
        except asyncio.TimeoutError:
            logger.warning(f"Task {task_id} timed out after {task.timeout_seconds}s")
            await self._handle_task_failure(run_id, task, "TimeoutError", ErrorType.TIMEOUT_ERROR)
        except SemanticException as e:
            logger.error(f"Task {task_id} semantic failure: {e.message}")
            await self._handle_task_failure(run_id, task, e.message, ErrorType.SEMANTIC_ERROR, e.reason)
        except Exception as e:
            logger.error(f"Task {task_id} failed: {e}")
            traceback.print_exc()
            error_type = self._classify_error(e)
            await self._handle_task_failure(run_id, task, str(e), error_type)

    # ══════════════════════════════════════════════════════════════════
    #  INTERPOLATION ENGINE
    # ══════════════════════════════════════════════════════════════════

    def _interpolate(self, val, run):
        """Recursively resolve {{ tasks.<id>.output.<path> }} expressions."""
        if isinstance(val, dict):
            return {k: self._interpolate(v, run) for k, v in val.items()}
        elif isinstance(val, list):
            return [self._interpolate(v, run) for v in val]
        elif isinstance(val, str):
            pattern = r"\{\{\s*(.*?)\s*\}\}"
            def replacer(match):
                expr = match.group(1)
                parts = expr.split('.')
                if len(parts) >= 3 and parts[0] == 'tasks':
                    target_task_id = parts[1]
                    target_task = next((t for t in run.tasks if t.task_id == target_task_id), None)
                    if target_task and target_task.output_data:
                        curr = target_task.output_data
                        start_idx = 3 if parts[2] == 'output' else 2
                        for p in parts[start_idx:]:
                            if isinstance(curr, dict) and p in curr:
                                curr = curr[p]
                            else:
                                return ""
                        return str(curr) if not isinstance(curr, (dict, list)) else json.dumps(curr)
                return match.group(0)
            return re.sub(pattern, replacer, val)
        return val

    # ══════════════════════════════════════════════════════════════════
    #  CORE DETERMINISTIC NODES (No LLM)
    # ══════════════════════════════════════════════════════════════════

    async def _execute_core_node(self, task, interpolated_input: dict, run) -> dict:
        """Execute a deterministic core node. Lightning-fast, no LLM."""
        
        if task.agent == "core.http":
            url = interpolated_input.get("url", "")
            method = interpolated_input.get("method", "GET").upper()
            headers = interpolated_input.get("headers", {})
            body = interpolated_input.get("body", None)
            timeout = interpolated_input.get("timeout", 30)
            
            async with httpx.AsyncClient(timeout=timeout) as client:
                req_kwargs = {"headers": headers}
                if body and method in ["POST", "PUT", "PATCH"]:
                    if isinstance(body, dict):
                        req_kwargs["json"] = body
                    elif isinstance(body, str):
                        try:
                            req_kwargs["json"] = json.loads(body)
                        except json.JSONDecodeError:
                            req_kwargs["content"] = body
                
                resp = await client.request(method, url, **req_kwargs)
                try:
                    return {"status_code": resp.status_code, "data": resp.json()}
                except Exception:
                    return {"status_code": resp.status_code, "data": resp.text}

        elif task.agent == "core.set":
            return interpolated_input.get("fields", {})

        elif task.agent == "core.if":
            condition_str = str(interpolated_input.get("condition", "false"))
            import ast
            try:
                is_true = bool(ast.literal_eval(condition_str))
            except (ValueError, SyntaxError):
                is_true = condition_str.lower() in ['true', '1', 'yes']
            if not is_true:
                task.status = TaskStatus.SKIPPED
            return {"matched": is_true, "condition": condition_str}

        elif task.agent == "core.merge":
            merged = {}
            for dep_id in task.dependencies:
                dep_task = next((t for t in run.tasks if t.task_id == dep_id), None)
                if dep_task and dep_task.output_data:
                    merged[dep_id] = dep_task.output_data
            return {"merged": merged}

        elif task.agent == "core.loop":
            items = interpolated_input.get("items", [])
            field = interpolated_input.get("field", None)
            if field and not items:
                parts = field.split(".")
                if len(parts) >= 2:
                    source_task = next((t for t in run.tasks if t.task_id == parts[0]), None)
                    if source_task and source_task.output_data:
                        curr = source_task.output_data
                        for p in parts[1:]:
                            if isinstance(curr, dict) and p in curr:
                                curr = curr[p]
                            else:
                                curr = []
                                break
                        if isinstance(curr, list):
                            items = curr
            return {"items": items, "count": len(items)}

        elif task.agent == "core.email":
            from backend.services import email_service
            from backend.services.email_service import EmailError
            tool_router = getattr(self.agent_factory, "tool_router", None) if self.agent_factory else None
            secrets_repo = getattr(tool_router, "secrets_repo", None)
            to = interpolated_input.get("to", "")
            recipients = [a.strip() for a in to.split(",") if a.strip()] if isinstance(to, str) else list(to)
            subject = str(interpolated_input.get("subject", ""))
            body = str(interpolated_input.get("body", ""))
            try:
                return await email_service.send_email(
                    secrets_repo,
                    run.user_id,
                    recipients,
                    subject,
                    body,
                    html=bool(interpolated_input.get("html", False)),
                )
            except EmailError as exc:
                draft = (
                    f"I wrote the email but could not send it ({exc}).\n\n"
                    f"To: {', '.join(recipients) or '[recipient]'}\nSubject: {subject}\n\n{body}\n\n"
                    "Add a Vault credential named `smtp` with host, port, username, and password to send mail."
                )
                return {
                    "sent": False,
                    "error": str(exc),
                    "reply": draft,
                    "message": draft,
                    "to": recipients,
                    "subject": subject,
                    "body": body,
                }
            except Exception as exc:
                draft = (
                    f"I wrote the email but sending failed ({exc}).\n\n"
                    f"To: {', '.join(recipients) or '[recipient]'}\nSubject: {subject}\n\n{body}"
                )
                return {"sent": False, "error": str(exc), "reply": draft, "message": draft}

        elif task.agent == "core.health":
            from backend.services.website_health import check_website
            url = interpolated_input.get("url") or interpolated_input.get("target") or ""
            return await check_website(str(url))

        elif task.agent == "core.chat":
            from backend.services import gemini_client
            prompt = str(interpolated_input.get("prompt") or interpolated_input.get("goal") or run.goal or "").strip()
            instruction = (
                "You are AgentOS, an autonomous workspace. Answer in a short, friendly chat message. "
                "You can plan work, build MCP tools for ANY app or HTTP API from a description, "
                "call live HTTPS APIs, check site health, and draft email. "
                "Do not invent live API results. Do not say you are limited to Stripe or Gmail.\n\nUser: "
            )
            try:
                text = await gemini_client.generate_text(instruction + prompt)
                text = (text or "").strip() or "I am here. Tell me what you want done."
                return {"reply": text, "message": text}
            except Exception as exc:
                fallback = (
                    "I can plan work, build MCP tools for any app or HTTP API you name, "
                    "call live HTTPS endpoints, check if a site is up, generate a small app in Studio, "
                    "and keep keys encrypted in the vault. Name an app or paste an OpenAPI URL and I will build the tools."
                )
                if gemini_client.is_quota_error(exc) or "quota" in str(exc).lower():
                    return {"reply": fallback, "message": fallback, "quota": True}
                logger.warning("core.chat failed: %s", exc)
                return {"reply": fallback, "message": fallback}

        elif task.agent == "core.mcp_build":
            from backend.agents.mcp_factory.mcp_factory_agent import MCPFactoryAgent
            tool_router = getattr(self.agent_factory, "tool_router", None) if self.agent_factory else None
            mcp_repo = getattr(tool_router, "mcp_repo", None) if tool_router else None
            secrets_repo = getattr(tool_router, "secrets_repo", None) if tool_router else None
            if mcp_repo is None and self.agent_factory:
                mcp_repo = getattr(self.agent_factory, "mcp_repo", None)
            if not mcp_repo:
                raise RuntimeError("MCP repository is not available")
            factory = MCPFactoryAgent(mcp_repo, secrets_repo=secrets_repo)
            result = await factory.run_build(
                user_id=run.user_id,
                method=str(interpolated_input.get("method") or "spec"),
                source=str(interpolated_input.get("source") or interpolated_input.get("url") or ""),
                name=str(interpolated_input.get("name") or ""),
                auth_type=str(interpolated_input.get("auth_type") or "API_KEY"),
            )
            if isinstance(result, dict) and result.get("status") == "error":
                raise RuntimeError(result.get("message") or "MCP build failed")
            return result

        else:
            return {"error": f"Unknown core node type: {task.agent}"}

    # ══════════════════════════════════════════════════════════════════
    #  AI AGENT EXECUTION (LLM-powered)
    # ══════════════════════════════════════════════════════════════════

    async def _execute_ai_agent(self, task, run, run_id: str, task_id: str, interpolated_input: Optional[dict] = None) -> str:
        """Execute a task using an AI agent."""
        
        snapshot_version = getattr(run, 'snapshot_version', None)
        agent_id = getattr(task, 'agent_id', None)
        
        context = {
            "run_id": run_id,
            "task_id": task_id,
            "workflow_id": run.workflow_id,
            "user_id": run.user_id
        }
        # Default: semi-autonomous (LOW/MEDIUM risk auto-runs; HIGH/CRITICAL needs approval).
        # Users can raise or lower this in settings.
        from backend.models.security import AutonomyLevel
        context["autonomy_level"] = AutonomyLevel.L2_SEMI_AUTONOMOUS
        if self.settings_repo:
            try:
                user_settings = await maybe_await(self.settings_repo.get_settings(run.user_id))
                if user_settings and "autonomy_level" in user_settings:
                    context["autonomy_level"] = AutonomyLevel(int(user_settings["autonomy_level"]))
            except Exception:
                logger.exception("Failed to load user autonomy settings for %s", run.user_id)
        approved_req_id = task.input_data.get("_approved_request_id")
        if approved_req_id:
            context["approved_request"] = await maybe_await(self.repo.get_approval(approved_req_id))

        catalog = []
        catalog_json = "[]"
        tool_router = self.agent_factory.tool_router if self.agent_factory else None

        if agent_id and self.agent_factory:
            agent = self.agent_factory.build_agent(agent_id, context=context)
            if not agent:
                raise ValueError(f"Plugin agent {agent_id} could not be resolved.")
        else:
            from backend.services.embedding_service import GoogleCloudEmbeddingService
            from backend.agents.context_manager import context_manager

            catalog = await tool_router.get_tool_catalog(run.user_id) if tool_router else []
            catalog_json = json.dumps(catalog)

            prev_tasks = [t.model_dump(mode="json") for t in run.tasks if t.status in [TaskStatus.COMPLETED, TaskStatus.FAILED] and t.task_id != task.task_id]
            ctx_data = context_manager.build_context(prev_tasks)
            workflow_context_str = f"Summary of older tasks:\n{ctx_data['older_summary']}\n\nRecent tasks:\n{json.dumps(ctx_data['recent_tasks'], indent=2)}"

            agent = get_orchestrator_agent(
                tool_router=tool_router,
                catalog_json=catalog_json,
                memory_repo=self.memory_repo,
                embedding_service=GoogleCloudEmbeddingService(),
                user_id=run.user_id,
                workflow_context=workflow_context_str,
                execution_context=context,
            )

        task_input = interpolated_input if interpolated_input is not None else task.input_data
        prompt = (
            f"Overall goal: {run.goal}\n"
            f"Current task: {task.task_id}\n"
            f"Requested tool (if any): {task.tool or 'none'}\n"
            f"Task input:\n{json.dumps(task_input, indent=2, default=str)}"
        )

        def extract_event_payload(events):
            texts = []
            tool_results = []
            for event in events or []:
                output = getattr(event, "output", None)
                if output is not None:
                    if hasattr(output, "model_dump"):
                        return output.model_dump()
                    if isinstance(output, dict):
                        return output
                    texts.append(str(output))
                content = getattr(event, "content", None)
                parts = getattr(content, "parts", None) if content else None
                if not parts:
                    continue
                for part in parts:
                    text = getattr(part, "text", None)
                    if text:
                        texts.append(str(text))
                    fr = getattr(part, "function_response", None)
                    if fr is not None:
                        payload = getattr(fr, "response", None)
                        if payload is None:
                            payload = getattr(fr, "result", None)
                        if payload is not None:
                            tool_results.append(payload)
            if texts:
                last = str(texts[-1]).strip()
                out = {"reply": last, "message": last}
                if tool_results:
                    out["tool_result"] = tool_results[-1]
                return out
            if tool_results:
                blob = json.dumps(tool_results[-1], default=str)
                return {"reply": blob[:8000], "message": blob[:8000], "tool_result": tool_results[-1]}
            return ""

        try:
            runner = InMemoryRunner(agent=agent, app_name=settings.APP_NAME)
            events = await runner.run_debug(prompt)
        except Exception as e:
            from backend.services import gemini_client
            msg = str(e)
            if not (gemini_client.is_quota_error(e) or "429" in msg or "RESOURCE_EXHAUSTED" in msg):
                raise
            tool_result = None
            browse_out = None
            if tool_router and catalog:
                tool_result = await self._call_matching_catalog_tool(run, catalog, tool_router, context)
            try:
                from backend.engine.direct_plan import _url, _wants_browse
                goal_text = str(run.goal or "")
                start_url = _url(goal_text)
                if _wants_browse(goal_text, start_url) and start_url:
                    from backend.services.web_agent import WebAgent
                    secrets_repo = getattr(tool_router, "secrets_repo", None) if tool_router else None
                    browse_out = await WebAgent(secrets_repo=secrets_repo).run(
                        goal=goal_text,
                        start_url=start_url,
                        user_id=run.user_id,
                        max_steps=20,
                    )
            except Exception as be:
                browse_out = {"success": False, "error": str(be)[:400]}
            try:
                text = await gemini_client.generate_text(
                    "You are AgentOS. Complete the user's goal using this context. "
                    "Do not invent live API data if a tool_result is present — summarize it.\n\n"
                    f"{prompt}\n\nTool catalog:\n{catalog_json[:12000]}\n\n"
                    f"Live tool_result:\n{json.dumps(tool_result, default=str)[:8000]}\n\n"
                    f"Browser result:\n{json.dumps(browse_out, default=str)[:8000]}"
                )
            except Exception:
                if browse_out:
                    text = json.dumps(browse_out, default=str)[:8000]
                elif tool_result is not None:
                    text = json.dumps(tool_result, default=str)[:8000]
                else:
                    text = (
                        "Gemini quota is exhausted for this step. Add your own Gemini key or an xAI Grok key "
                        "in Settings, then retry."
                    )
            out = {"reply": text, "message": text, "fallback": "llm"}
            if tool_result is not None:
                out["tool_result"] = tool_result
            if browse_out is not None:
                out["browse"] = browse_out
            return out

        raw = extract_event_payload(events)
        if isinstance(raw, dict):
            reply = str(raw.get("reply") or raw.get("message") or "").strip()
            if reply:
                raw.setdefault("reply", reply)
                raw.setdefault("message", reply)
                return raw
            if raw.get("tool_result") is not None:
                blob = json.dumps(raw["tool_result"], default=str)[:8000]
                raw["reply"] = blob
                raw["message"] = blob
                return raw
        text = str(raw or "").strip()
        if text:
            return {"reply": text, "message": text}
        if tool_router and catalog:
            tool_result = await self._call_matching_catalog_tool(run, catalog, tool_router, context)
            if tool_result is not None:
                blob = json.dumps(tool_result, default=str)[:8000]
                return {"reply": blob, "message": blob, "tool_result": tool_result, "fallback": "catalog_tool"}
        return {"reply": text, "message": text}

    # ══════════════════════════════════════════════════════════════════
    #  FAILURE HANDLING & SELF-HEALING
    # ══════════════════════════════════════════════════════════════════

    async def _handle_task_failure(self, run_id: str, task: Task, error_msg: str, error_type: str, semantic_reason: Optional[SemanticErrorReason] = None) -> None:
        task.error = error_msg
        task.error_type = error_type
        
        total_attempts = task.attempt + task.recovery_attempts
        
        if total_attempts >= task.max_total_attempts:
            logger.error(f"Task {task.task_id} exhausted max_total_attempts ({task.max_total_attempts}). Failing permanently.")
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.now(timezone.utc)
            await persist_task(self.repo, run_id, task)
            self._emit_event(WorkflowEventType.TASK_FAILED, run_id, task.workflow_id, task.task_id, task.status, f"Task {task.task_id} failed", metadata={"error": error_msg, "error_type": error_type})
            asyncio.create_task(self.evaluate_dag(run_id))
            return

        # Self-Healing Recovery
        if error_type == ErrorType.SEMANTIC_ERROR and task.recovery_enabled and task.recovery_attempts < task.max_recoveries:
            task.status = TaskStatus.RECOVERING
            if task.original_input is None:
                task.original_input = task.input_data.copy()
            await persist_task(self.repo, run_id, task)
            logger.info(f"Task {task.task_id} entered RECOVERING state. Attempt {task.recovery_attempts + 1}/{task.max_recoveries}")
            self._emit_event(WorkflowEventType.TASK_RECOVERING, run_id, task.workflow_id, task.task_id, task.status, f"Task {task.task_id} recovering (attempt {task.recovery_attempts + 1})")
            
            async def trigger_recovery():
                event = TaskRecoveryEvent(
                    workflow_id=task.workflow_id,
                    run_id=run_id,
                    task_id=task.task_id,
                    recovery_attempt=task.recovery_attempts + 1
                )
                await self.message_bus.publish("agentos-recovery-events", event)
                
            asyncio.create_task(trigger_recovery())
            return

        if error_type in [ErrorType.TRANSIENT_ERROR, ErrorType.TIMEOUT_ERROR] and task.attempt < task.max_retries:
            task.status = TaskStatus.RETRYING
            await persist_task(self.repo, run_id, task)
            delay = self._calculate_backoff(task.attempt)
            logger.info(f"Task {task.task_id} will be retried in {delay:.2f}s")
            self._emit_event(WorkflowEventType.TASK_RETRYING, run_id, task.workflow_id, task.task_id, task.status, f"Task {task.task_id} retrying in {delay:.1f}s")
            
            async def delayed_trigger():
                await asyncio.sleep(delay)
                event = TaskTriggerEvent(
                    workflow_id=task.workflow_id,
                    run_id=run_id,
                    task_id=task.task_id
                )
                await self.message_bus.publish("agentos-workflow-events", event)
                
            asyncio.create_task(delayed_trigger())
        else:
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.now(timezone.utc)
            await persist_task(self.repo, run_id, task)
            self._emit_event(WorkflowEventType.TASK_FAILED, run_id, task.workflow_id, task.task_id, task.status, f"Task {task.task_id} failed", metadata={"error": error_msg, "error_type": error_type})
            asyncio.create_task(self.evaluate_dag(run_id))

    @staticmethod
    def _classify_error(exc: Exception) -> str:
        msg = str(exc).lower()
        if any(x in msg for x in ("timeout", "timed out", "deadline")):
            return ErrorType.TIMEOUT_ERROR
        if any(x in msg for x in (
            "429", "quota", "resource_exhausted", "network", "temporarily",
            "connection", "503", "502", "econnreset", "unavailable", "overloaded",
        )):
            return ErrorType.TRANSIENT_ERROR
        if any(x in msg for x in ("ssrf", "unauthorized", "401", "403", "captcha", "mfa", "otp")):
            return ErrorType.AUTHORIZATION_ERROR
        if any(x in msg for x in ("unknown tool", "missing tool", "no integration")):
            return ErrorType.SEMANTIC_ERROR
        return ErrorType.INTERNAL_ERROR
