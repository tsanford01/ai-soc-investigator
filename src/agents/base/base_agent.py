"""Base agent implementation providing core functionality for all agents."""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging
import uuid
import asyncio
from datetime import datetime

from src.agents.registry import AgentRegistry
from src.utils.retry import RetryConfig

logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    """Base class for all agents in the system."""

    def __init__(
        self, 
        registry: AgentRegistry,
        retry_config: Optional[RetryConfig] = None
    ) -> None:
        """Initialize base agent."""
        self.registry = registry
        self.agent_id = str(uuid.uuid4())
        self._retry_config = retry_config or RetryConfig()
        self.initialized = False

    async def initialize(self) -> None:
        """Initialize the agent."""
        if not self.initialized:
            await self._setup_agent()
            self.initialized = True

    async def _setup_agent(self) -> None:
        """Setup agent and register capabilities."""
        await self._initialize_capabilities()

    @abstractmethod
    async def _initialize_capabilities(self) -> None:
        """Initialize agent capabilities. Must be implemented by subclasses."""
        pass

    async def _process_capability_request(self, request_data: Dict[str, Any]) -> Any:
        """Process a capability request."""
        capability_name = request_data.get("capability")
        if not capability_name:
            raise ValueError("No capability specified in request")

        handler = await self.registry.get_capability(capability_name)
        if not handler:
            raise ValueError(f"Capability not found: {capability_name}")

        params = request_data.get("params", {})
        return await handler(**params)
