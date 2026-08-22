from abc import ABC, abstractmethod
from typing import Callable, Any, Awaitable
from backend.models.schemas import TaskTriggerEvent

class MessageBus(ABC):
    @abstractmethod
    async def publish(self, topic: str, message: TaskTriggerEvent) -> None:
        """Publish a message to a topic."""
        pass
        
    @abstractmethod
    async def consume(self, topic: str, handler: Callable[[TaskTriggerEvent, 'MessageContext'], Awaitable[None]]) -> None:
        """Consume messages from a topic and invoke the handler."""
        pass

class MessageContext(ABC):
    @abstractmethod
    async def ack(self) -> None:
        """Acknowledge the message (successful processing)."""
        pass
        
    @abstractmethod
    async def nack(self) -> None:
        """Negative acknowledge the message (failed processing, should retry)."""
        pass
