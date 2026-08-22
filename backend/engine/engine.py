import asyncio
import logging
import random
from typing import Optional
from datetime import datetime, timezone
from backend.models.schemas import Task, TaskStatus, ErrorType, TaskTriggerEvent
from backend.repositories.workflow_repository import WorkflowRepository
from backend.repositories.message_bus import MessageBus
from backend.agents.orchestrator.orchestrator_agent import get_orchestrator_agent
from google.adk.runners import InMemoryRunner
from backend.config.settings import settings

logger = logging.getLogger(__name__)

class WorkflowEngine:
    def __init__(self, workflow_repo: WorkflowRepository, message_bus: MessageBus):
        self.repo = workflow_repo
        self.message_bus = message_bus

    async def evaluate_dag(self, run_id: str) -> None:
        """
        Evaluate the DAG for a given run and trigger ready tasks.
        A task is ready if its dependencies are COMPLETED.
        """
        run = self.repo.get_run(run_id)
        if not run:
            logger.error(f"Run {run_id} not found during DAG evaluation")
            return
            
        if run.status == TaskStatus.CANCELLED:
            logger.info(f"Run {run_id} is cancelled. Skipping evaluation.")
            return

        completed_tasks = {t.task_id for t in run.tasks if t.status == TaskStatus.COMPLETED}
        failed_or_cancelled_tasks = {t.task_id for t in run.tasks if t.status in [TaskStatus.FAILED, TaskStatus.CANCELLED]}
        
        all_completed = True
        
        for task in run.tasks:
            if task.status in [TaskStatus.PENDING, TaskStatus.WAITING]:
                # Check dependencies
                deps_met = True
                deps_failed = False
                for dep in task.dependencies:
                    if dep in failed_or_cancelled_tasks:
                        deps_failed = True
                        break
                    if dep not in completed_tasks:
                        deps_met = False
                        break
                        
                if deps_failed:
                    task.status = TaskStatus.BLOCKED
                    self.repo.update_task(run_id, task)
                    logger.info(f"Task {task.task_id} BLOCKED due to failed dependencies")
                    # Note: we do not set all_completed = False because BLOCKED is a terminal state
                elif deps_met:
                    # It's ready, but we keep it PENDING until a worker claims it.
                    # WAITING -> PENDING if it was WAITING
                    if task.status == TaskStatus.WAITING:
                        task.status = TaskStatus.PENDING
                        self.repo.update_task(run_id, task)
                        
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
                    # Still waiting
                    if task.status == TaskStatus.PENDING:
                        task.status = TaskStatus.WAITING
                        self.repo.update_task(run_id, task)
                    all_completed = False
            elif task.status not in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED, TaskStatus.BLOCKED]:
                all_completed = False

        if all_completed and run.status not in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            # Check if any tasks failed or blocked
            any_failed = any(t.status in [TaskStatus.FAILED, TaskStatus.BLOCKED] for t in run.tasks)
            if any_failed:
                run.status = TaskStatus.FAILED
            else:
                run.status = TaskStatus.COMPLETED
            self.repo.save_run(run)
            logger.info(f"Run {run_id} marked as {run.status}")

    def _calculate_backoff(self, attempt: int) -> float:
        """Exponential backoff with jitter."""
        base_delay = 2.0
        max_delay = 60.0
        delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
        jitter = random.uniform(0, 0.1 * delay)
        return delay + jitter

    async def execute_task(self, run_id: str, task_id: str) -> None:
        """Execute a task."""
        run = self.repo.get_run(run_id)
        if not run:
            return
            
        task = next((t for t in run.tasks if t.task_id == task_id), None)
        if not task:
            return
            
        if run.status == TaskStatus.CANCELLED:
            task.status = TaskStatus.CANCELLED
            self.repo.update_task(run_id, task)
            return

        # Attempt atomic claim
        lease_seconds = max(task.timeout_seconds + 10, 60)
        claimed = self.repo.claim_task(run_id, task_id, lease_seconds)
        if not claimed:
            logger.info(f"Task {task_id} already claimed or completed.")
            return

        # Fetch fresh task state after claim
        run = self.repo.get_run(run_id)
        task = next((t for t in run.tasks if t.task_id == task_id), None)
        
        try:
            # Execute with timeout
            async def _run_agent():
                # Phase 2: OrchestratorAgent only for simplicity, but can be dynamic
                agent = get_orchestrator_agent()
                runner = InMemoryRunner(agent=agent, app_name=settings.APP_NAME)
                # In real app, we pass task.input_data
                events = await runner.run_debug(f"Execute step: {task.task_id}")
                return str(events[-1].output) if events else ""
                
            result = await asyncio.wait_for(_run_agent(), timeout=task.timeout_seconds)
            
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now(timezone.utc)
            task.output_data = {"result": result}
            self.repo.update_task(run_id, task)
            logger.info(f"Task {task_id} completed successfully.")
            
            # Evaluate DAG for downstream tasks
            await self.evaluate_dag(run_id)
            
        except asyncio.TimeoutError:
            logger.warning(f"Task {task_id} timed out after {task.timeout_seconds}s")
            self._handle_task_failure(run_id, task, "TimeoutError", ErrorType.RETRYABLE)
        except Exception as e:
            logger.error(f"Task {task_id} failed: {e}")
            # Simplified error categorization
            error_type = ErrorType.RETRYABLE if "network" in str(e).lower() else ErrorType.NON_RETRYABLE
            self._handle_task_failure(run_id, task, str(e), error_type)

    def _handle_task_failure(self, run_id: str, task: Task, error_msg: str, error_type: str) -> None:
        task.error = error_msg
        task.error_type = error_type
        
        if error_type == ErrorType.RETRYABLE and task.attempt < task.max_retries:
            task.status = TaskStatus.RETRYING
            self.repo.update_task(run_id, task)
            delay = self._calculate_backoff(task.attempt)
            logger.info(f"Task {task.task_id} will be retried in {delay:.2f}s")
            
            # Schedule retry asynchronously
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
            self.repo.update_task(run_id, task)
            
            # This failure blocks downstream tasks, evaluate DAG
            asyncio.create_task(self.evaluate_dag(run_id))
