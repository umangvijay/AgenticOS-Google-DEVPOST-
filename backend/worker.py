import logging
import asyncio
from backend.models.schemas import TaskTriggerEvent, WorkflowRun, Task, TaskStatus
from backend.models.schedule import SchedulerTriggerEvent
from backend.repositories.message_bus import MessageBus, MessageContext
from backend.repositories.schedule_repository import ScheduleRepository
from backend.engine.engine import WorkflowEngine
import hashlib

logger = logging.getLogger(__name__)

async def start_worker(message_bus: MessageBus, workflow_engine: WorkflowEngine, schedule_repo: ScheduleRepository = None):
    logger.info("Worker started, listening for events...")
    
    async def handle_event(event: TaskTriggerEvent, ctx: MessageContext):
        try:
            logger.info(f"Worker processing task {event.task_id} for run {event.run_id}")
            # execute_task will claim the task, execute it, and update its state
            # If it throws, we should NACK so it can be retried (or handled by engine)
            # Actually, engine.execute_task catches its own errors and decides to RETRY or FAIL.
            # So execute_task itself shouldn't raise unhandled exceptions unless something catastrophic happens.
            await workflow_engine.execute_task(event.run_id, event.task_id)
            
            # Since the engine handled the execution and state update, we can ACK the message.
            # If the engine decided to RETRY, it published a NEW message with a delay.
            await ctx.ack()
        except Exception as e:
            logger.error(f"Worker encountered unhandled exception: {e}")
            await ctx.nack()

    # We will gather all consumers at the end
    
    async def handle_schedule(event: dict, ctx: MessageContext):
        try:
            if not schedule_repo:
                await ctx.ack()
                return
                
            logger.info(f"Worker received schedule trigger: {event}")
            # Ensure the event matches SchedulerTriggerEvent
            trigger = SchedulerTriggerEvent(**event)
            schedule = schedule_repo.get_schedule(trigger.schedule_id)
            
            if not schedule or schedule.status != "ACTIVE":
                logger.warning(f"Schedule {trigger.schedule_id} not found or not ACTIVE")
                await ctx.ack()
                return
                
            # Create idempotency key: schedule_id + logical scheduled time in UTC
            scheduled_time_str = trigger.scheduled_time.isoformat()
            execution_key = f"{schedule.schedule_id}|{scheduled_time_str}"
            run_id = "sch-" + hashlib.sha256(execution_key.encode("utf-8")).hexdigest()
            
            # Construct a dynamic WorkflowRun containing the goal
            run = WorkflowRun(
                run_id=run_id,
                user_id=schedule.user_id,
                goal=schedule.goal,
                status=TaskStatus.PENDING,
                tasks=[]
            )
            
            # Atomic creation to prevent race conditions on duplicate delivery
            created = workflow_engine.repo.create_if_absent(run)
            
            if created:
                logger.info(f"Successfully enqueued new run {run_id} for schedule {schedule.schedule_id}")
                # We could enqueue an orchestrator task here, or just evaluate the DAG directly
                # For Phase 2 compatibility, we create the root orchestrator task
                root_task = Task(
                    task_id=f"root-{run_id}",
                    workflow_id=run.workflow_id,
                    run_id=run_id,
                    agent="OrchestratorAgent",
                    input_data={"goal": schedule.goal},
                    status=TaskStatus.PENDING,
                    dependencies=[]
                )
                run.tasks.append(root_task)
                workflow_engine.repo.update_task(run_id, root_task) # Actually we should save the run with the task
                workflow_engine.repo.save_run(run) # Overwrite with tasks
                
                await workflow_engine.evaluate_dag(run_id)
            else:
                logger.info(f"Run {run_id} already exists for schedule {schedule.schedule_id}. Skipping.")
                
            await ctx.ack()
        except Exception as e:
            logger.error(f"Worker encountered error processing schedule trigger: {e}")
            await ctx.nack()

    await asyncio.gather(
        message_bus.consume("agentos-workflow-events", handle_event),
        message_bus.consume("agentos-scheduler-triggers", handle_schedule)
    )
