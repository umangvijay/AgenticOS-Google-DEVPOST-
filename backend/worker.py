import logging
import asyncio
from backend.models.schemas import TaskTriggerEvent
from backend.repositories.message_bus import MessageBus, MessageContext
from backend.engine.engine import WorkflowEngine

logger = logging.getLogger(__name__)

async def start_worker(message_bus: MessageBus, workflow_engine: WorkflowEngine):
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

    await message_bus.consume("agentos-workflow-events", handle_event)
