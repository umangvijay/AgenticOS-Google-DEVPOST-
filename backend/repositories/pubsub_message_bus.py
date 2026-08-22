import json
import logging
from typing import Callable, Awaitable
from backend.models.schemas import TaskTriggerEvent
from backend.repositories.message_bus import MessageBus, MessageContext
from backend.config.settings import settings

logger = logging.getLogger(__name__)

class PubSubMessageContext(MessageContext):
    def __init__(self, message):
        self.message = message
        
    async def ack(self) -> None:
        self.message.ack()
        
    async def nack(self) -> None:
        self.message.nack()

class PubSubMessageBus(MessageBus):
    def __init__(self):
        # We only import google.cloud.pubsub when instantiated to avoid failing fast in tests
        from google.cloud import pubsub_v1
        self.publisher = pubsub_v1.PublisherClient()
        self.subscriber = pubsub_v1.SubscriberClient()
        self.project_id = settings.GOOGLE_CLOUD_PROJECT
        
    async def publish(self, topic: str, message: TaskTriggerEvent) -> None:
        topic_path = self.publisher.topic_path(self.project_id, topic)
        data = message.model_dump_json().encode("utf-8")
        future = self.publisher.publish(topic_path, data)
        # publisher.publish is synchronous but returns a future. For a fully async implementation, 
        # we would wrap this in asyncio.wrap_future or run_in_executor
        future.result()
        logger.info(f"Published to {topic_path}: {message.task_id}")
        
    async def consume(self, topic: str, handler: Callable[[TaskTriggerEvent, MessageContext], Awaitable[None]]) -> None:
        # Note: this is a simplistic async wrapper for GCP Pub/Sub for Phase 2
        # A true production ready consumer might use asyncio integration or a blocking thread pool
        subscription_path = self.subscriber.subscription_path(self.project_id, f"{topic}-sub")
        
        def callback(message):
            try:
                data = json.loads(message.data.decode("utf-8"))
                event = TaskTriggerEvent(**data)
                ctx = PubSubMessageContext(message)
                
                # We need to run the async handler from a sync callback
                # In a real async framework we'd schedule this on the event loop
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(handler(event, ctx))
                else:
                    asyncio.run(handler(event, ctx))
            except Exception as e:
                logger.error(f"Error parsing pubsub message: {e}")
                message.nack()
                
        self.subscriber.subscribe(subscription_path, callback=callback)
        logger.info(f"Listening on {subscription_path}")
        
        # Keep alive
        import asyncio
        while True:
            await asyncio.sleep(3600)
