"""Agent registry for managing capabilities and events."""
import asyncio
import logging
from typing import Dict, Any, Callable, Coroutine, List

logger = logging.getLogger(__name__)

class AgentRegistry:
    """Registry for managing agent capabilities and events."""

    def __init__(self) -> None:
        """Initialize the registry."""
        self.capabilities: Dict[str, Callable[..., Coroutine[Any, Any, Any]]] = {}
        self.event_queues: Dict[str, List[asyncio.Queue]] = {}

    async def register_capability(
        self,
        capability_name: str,
        handler: Callable[..., Coroutine[Any, Any, Any]]
    ) -> None:
        """Register a capability with a handler function."""
        self.capabilities[capability_name] = handler
        logger.info(f"Registered capability: {capability_name}")

    async def unregister_capability(self, capability_name: str) -> None:
        """Unregister a capability."""
        if capability_name in self.capabilities:
            del self.capabilities[capability_name]
            logger.info(f"Unregistered capability: {capability_name}")

    async def get_capability(
        self,
        capability_name: str
    ) -> Callable[..., Coroutine[Any, Any, Any]]:
        """Get a capability handler by name."""
        if capability_name not in self.capabilities:
            raise ValueError(f"Capability not found: {capability_name}")
        return self.capabilities[capability_name]

    async def subscribe_to_event(self, event_name: str) -> asyncio.Queue:
        """Subscribe to an event and get a queue for receiving events."""
        if event_name not in self.event_queues:
            self.event_queues[event_name] = []
        queue = asyncio.Queue()
        self.event_queues[event_name].append(queue)
        logger.info(f"Subscribed to event: {event_name}")
        return queue

    async def unsubscribe_from_event(self, event_name: str, queue: asyncio.Queue) -> None:
        """Unsubscribe from an event."""
        if event_name in self.event_queues and queue in self.event_queues[event_name]:
            self.event_queues[event_name].remove(queue)
            logger.info(f"Unsubscribed from event: {event_name}")

    async def publish_event(self, event_name: str, data: Dict[str, Any]) -> None:
        """Publish an event to all subscribers."""
        if event_name in self.event_queues:
            event = {"name": event_name, "data": data}
            for queue in self.event_queues[event_name]:
                await queue.put(event)
            logger.info(f"Published event: {event_name}")
