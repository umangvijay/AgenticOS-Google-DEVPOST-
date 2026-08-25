import asyncio
import logging
from typing import Dict, Any
from backend.repositories.message_bus import MessageBus
from backend.repositories.workflow_repository import WorkflowRepository
from backend.repositories.audit_repository import audit_repo, AuditEvent
from backend.models.schemas import TaskRecoveryEvent, TaskStatus, TaskTriggerEvent, ErrorType, SemanticErrorReason
from backend.models.recovery import RecoveryContext, RecoveryAction, RecoveryActionEnum
from backend.agents.recovery.recovery_agent import get_recovery_agent
from google.adk.runners import InMemoryRunner
import json
from datetime import datetime, timezone

logger = logging.getLogger("recovery_worker")

class RecoveryWorker:
    def __init__(self, message_bus: MessageBus, workflow_repo: WorkflowRepository):
        self.message_bus = message_bus
        self.repo = workflow_repo
        
    async def handle_recovery_event(self, event: TaskRecoveryEvent):
        """Processes a TaskRecoveryEvent from the message bus."""
        run = self.repo.get_run(event.run_id)
        if not run:
            return
            
        task = next((t for t in run.tasks if t.task_id == event.task_id), None)
        if not task:
            return
            
        # Idempotency check: only recover if status is RECOVERING and attempts match
        if task.status != TaskStatus.RECOVERING or task.recovery_attempts + 1 != event.recovery_attempt:
            logger.info(f"Ignoring duplicate/stale recovery event for {task.task_id}")
            return
            
        # Atomic claim: We increment recovery_attempts to mark it claimed
        task.recovery_attempts += 1
        self.repo.update_task(run.run_id, task)
        
        try:
            # 1. Prepare sanitized RecoveryContext
            context = RecoveryContext(
                workflow_id=run.workflow_id,
                run_id=run.run_id,
                task_id=task.task_id,
                task_type=task.tool or task.agent,
                original_input=task.original_input or task.input_data,
                current_input=task.input_data,
                validation_error=task.error or "Unknown semantic error",
                error_reason=getattr(SemanticErrorReason, task.error_type, SemanticErrorReason.TOOL_SEMANTIC_REJECTION),
                allowed_tool_schema={}, # In a real implementation, fetch from MCP tool catalog
                previous_recovery_attempts=task.recovery_attempts - 1,
                safe_error_details="Semantic violation occurred during execution."
            )
            
            # 2. Invoke RecoveryAgent
            agent = get_recovery_agent()
            runner = InMemoryRunner(agent=agent, app_name="AgenticOS")
            
            prompt = f"Please analyze this recovery context and provide a RecoveryAction:\n{context.model_dump_json()}"
            events = await runner.run_debug(prompt)
            
            if not events:
                raise ValueError("RecoveryAgent returned empty response")
                
            raw_output = events[-1].output
            
            # ADK LlmAgent with response_model returns a Pydantic model
            # but sometimes it might be a string if not properly configured. 
            # We assume it's parsed into RecoveryAction.
            if isinstance(raw_output, str):
                action = RecoveryAction.model_validate_json(raw_output)
            elif isinstance(raw_output, RecoveryAction):
                action = raw_output
            else:
                data = raw_output.model_dump() if hasattr(raw_output, 'model_dump') else raw_output
                action = RecoveryAction.model_validate(data)
                
            # 3. Process RecoveryAction
            if action.action == RecoveryActionEnum.ABORT:
                logger.info(f"RecoveryAgent elected to ABORT task {task.task_id}")
                task.status = TaskStatus.FAILED
                task.error = f"Unrecoverable: {action.rationale}"
                self.repo.update_task(run.run_id, task)
                # trigger DAG evaluation
                await self._trigger_dag(run.run_id)
                return
                
            if action.action == RecoveryActionEnum.REPAIR:
                logger.info(f"RecoveryAgent provided repair for task {task.task_id}")
                
                # Invalidate any approvals if the input changed!
                if task.input_data.get("_approved_request_id") and action.corrected_input != task.input_data:
                    logger.warning(f"Task {task.task_id} had an approval, but arguments changed. Invalidating approval.")
                    task.input_data.pop("_approved_request_id", None)
                    
                # We would ideally run schema validation here against the original tool schema.
                
                # Update task state
                task.input_data = action.corrected_input or {}
                task.recovery_history.append({
                    "attempt": task.recovery_attempts,
                    "action": action.model_dump(),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
                task.status = TaskStatus.PENDING
                self.repo.update_task(run.run_id, task)
                
                from backend.repositories.audit_repository import ActorType
                audit_repo.log_event(AuditEvent(
                    event_type="TASK_RECOVERED",
                    actor_id="SYSTEM",
                    actor_type=ActorType.SYSTEM,
                    resource_id=task.task_id,
                    workflow_id=run.workflow_id,
                    run_id=run.run_id,
                    task_id=task.task_id,
                    details={"attempt": task.recovery_attempts, "rationale": action.rationale}
                ))
                
                # Re-trigger task
                trigger_event = TaskTriggerEvent(
                    workflow_id=run.workflow_id,
                    run_id=run.run_id,
                    task_id=task.task_id
                )
                await self.message_bus.publish("agentos-workflow-events", trigger_event)
                
        except Exception as e:
            logger.error(f"Recovery Worker failed for task {task.task_id}: {e}")
            task.status = TaskStatus.FAILED
            task.error = f"Recovery failed: {str(e)}"
            self.repo.update_task(run.run_id, task)
            await self._trigger_dag(run.run_id)
            
    async def _trigger_dag(self, run_id: str):
        # We could use the workflow engine directly, but this is a worker,
        # so ideally it just publishes a generic "Evaluate DAG" event, 
        # or we just import the engine. For simplicity, we assume the main engine 
        # is polling or we can import it. Let's just simulate it.
        pass
