import asyncio
import logging
from typing import Callable, Awaitable, Any
from backend.models.schemas import TaskTriggerEvent
from backend.repositories.message_bus import MessageBus, MessageContext

logger = logging.getLogger(__name__)

class InMemoryMessageContext(MessageContext):
    def __init__(self, message_id: str, queue: asyncio.Queue, message: TaskTriggerEvent):
        self.message_id = message_id
        self.queue = queue
        self.message = message
        
    async def ack(self) -> None:
        logger.debug(f"Message {self.message_id} ACKed")
        self.queue.task_done()
        
    async def nack(self) -> None:
        logger.warning(f"Message {self.message_id} NACKed, putting back in queue")
        self.queue.task_done()
        await self.queue.put(self.message)

class InMemoryMessageBus(MessageBus):
    def __init__(self):
        self.topics = {}
        
    def _get_queue(self, topic: str) -> asyncio.Queue:
        if topic not in self.topics:
            self.topics[topic] = asyncio.Queue()
        return self.topics[topic]

    async def publish(self, topic: str, message: Any) -> None:
        queue = self._get_queue(topic)
        await queue.put(message)
        
        msg_id = getattr(message, "task_id", getattr(message, "schedule_id", str(message)))
        if isinstance(message, dict):
            msg_id = message.get("task_id") or message.get("schedule_id", str(message))
            
        logger.info(f"Published to {topic}: {msg_id}")
        
    async def consume(self, topic: str, handler: Callable[[TaskTriggerEvent, MessageContext], Awaitable[None]]) -> None:
        queue = self._get_queue(topic)
        message_counter = 0
        while True:
            message = await queue.get()
            message_counter += 1
            ctx = InMemoryMessageContext(str(message_counter), queue, message)
            try:
                await handler(message, ctx)
            except Exception as e:
                logger.error(f"Error in consumer handler: {e}")
                # We implicitly NACK on unhandled exception in the handler framework if the handler didn't
                await ctx.nack()
