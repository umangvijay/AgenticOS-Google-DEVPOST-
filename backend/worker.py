import logging
import asyncio
from backend.models.schemas import TaskTriggerEvent, WorkflowRun, Task, TaskStatus
from backend.models.schedule import SchedulerTriggerEvent
from backend.repositories.message_bus import MessageBus, MessageContext
from backend.repositories.schedule_repository import ScheduleRepository
from backend.engine.engine import WorkflowEngine
from backend.engine.repo_adapter import maybe_await, persist_run
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
    
    async def handle_schedule(event, ctx: MessageContext):
        try:
            if not schedule_repo:
                await ctx.ack()
                return
                
            logger.info(f"Worker received schedule trigger: {event}")
            if isinstance(event, SchedulerTriggerEvent):
                trigger = event
            else:
                trigger = SchedulerTriggerEvent(**event)
            schedule = await maybe_await(schedule_repo.get_schedule(trigger.schedule_id))
            
            if not schedule or str(schedule.get("status", "")).upper() != "ACTIVE":
                logger.warning(f"Schedule {trigger.schedule_id} not found or not ACTIVE")
                await ctx.ack()
                return
                
            # Create idempotency key: schedule_id + logical scheduled time in UTC
            scheduled_time_str = trigger.scheduled_time.isoformat()
            execution_key = f"{trigger.schedule_id}|{scheduled_time_str}"
            run_id = "sch-" + hashlib.sha256(execution_key.encode("utf-8")).hexdigest()
            
            # Construct a dynamic WorkflowRun containing the goal
            run = WorkflowRun(
                run_id=run_id,
                user_id=schedule["user_id"],
                goal=schedule["goal"],
                status=TaskStatus.PENDING,
                tasks=[]
            )
            
            # Atomic creation to prevent race conditions on duplicate delivery
            created = await maybe_await(workflow_engine.repo.create_if_absent(run.model_dump(mode="json")))
            
            if created:
                logger.info(f"Successfully enqueued new run {run_id} for schedule {trigger.schedule_id}")
                root_task = Task(
                    task_id=f"root-{run_id}",
                    workflow_id=run.workflow_id,
                    run_id=run_id,
                    user_id=schedule["user_id"],
                    agent="OrchestratorAgent",
                    input_data={"goal": schedule["goal"]},
                    status=TaskStatus.PENDING,
                    dependencies=[]
                )
                run.tasks.append(root_task)
                await persist_run(workflow_engine.repo, run)
                try:
                    await maybe_await(schedule_repo.record_execution(trigger.schedule_id, run_id, "STARTED"))
                except Exception:
                    logger.warning("Failed to record schedule execution", exc_info=True)
                
                await workflow_engine.evaluate_dag(run_id)
            else:
                logger.info(f"Run {run_id} already exists for schedule {trigger.schedule_id}. Skipping.")
                
            await ctx.ack()
        except Exception as e:
            logger.error(f"Worker encountered error processing schedule trigger: {e}")
            await ctx.nack()

    async def cron_ticker():
        """Local scheduler: fire due cron schedules (Cloud Scheduler replaces this in prod)."""
        from datetime import datetime, timezone
        while True:
            try:
                if schedule_repo and hasattr(schedule_repo, "list_due_schedules"):
                    now = datetime.now(timezone.utc)
                    due = await maybe_await(schedule_repo.list_due_schedules(now.isoformat()))
                    for schedule in due:
                        trigger = SchedulerTriggerEvent(
                            schedule_id=schedule["schedule_id"], scheduled_time=now
                        )
                        await message_bus.publish(
                            "agentos-scheduler-triggers", trigger.model_dump(mode="json")
                        )
                        # Advance next_run_at so the schedule doesn't refire
                        try:
                            from croniter import croniter
                            cron = croniter(schedule.get("cron_expression") or "", now)
                            next_run = cron.get_next(datetime).isoformat()
                        except Exception:
                            next_run = None
                        await maybe_await(schedule_repo.update_schedule(
                            schedule["schedule_id"], {"next_run_at": next_run}
                        ))
            except Exception as e:
                logger.error(f"Cron ticker error: {e}")
            await asyncio.sleep(30)

    from backend.workers.recovery_worker import RecoveryWorker
    recovery_worker = RecoveryWorker(message_bus, workflow_engine.repo, workflow_engine)

    await asyncio.gather(
        message_bus.consume("agentos-workflow-events", handle_event),
        message_bus.consume("agentos-scheduler-triggers", handle_schedule),
        message_bus.consume("agentos-recovery-events", recovery_worker.handle_recovery_event),
        cron_ticker(),
    )
