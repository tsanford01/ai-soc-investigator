"""
Agent registry for managing agent capabilities and coordination.
"""
from typing import Dict, List, Any, Optional, Set
import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)

@dataclass
class AgentCapability:
    """
    Represents a capability that an agent can provide.
    """
    name: str
    description: str
    parameters: Dict[str, str]
    return_type: str

class AgentRegistry:
    """
    Central registry for managing agent capabilities and coordination.
    
    Responsibilities:
    - Track agent capabilities
    - Route capability requests
    - Manage agent status
    - Handle event distribution
    """
    
    def __init__(self):
        """Initialize the agent registry."""
        self._capabilities: Dict[str, Dict[str, AgentCapability]] = {}
        self._status: Dict[str, Dict[str, Any]] = {}
        self._subscribers: Dict[str, Set[str]] = {}
        self._event_subscribers: Dict[str, List[asyncio.Queue]] = defaultdict(list)
        self._lock = asyncio.Lock()
    
    async def register_capability(
        self, 
        agent_id: str, 
        capability: AgentCapability
    ) -> None:
        """
        Register a capability for an agent.
        
        Args:
            agent_id: ID of the agent
            capability: Capability to register
        """
        async with self._lock:
            if agent_id not in self._capabilities:
                self._capabilities[agent_id] = {}
            self._capabilities[agent_id][capability.name] = capability
            logger.info(f"Registered capability {capability.name} for agent {agent_id}")
    
    async def unregister_capability(
        self, 
        agent_id: str, 
        capability_name: str
    ) -> None:
        """
        Unregister a capability for an agent.
        
        Args:
            agent_id: ID of the agent
            capability_name: Name of capability to unregister
        """
        async with self._lock:
            if agent_id in self._capabilities:
                self._capabilities[agent_id].pop(capability_name, None)
                if not self._capabilities[agent_id]:
                    del self._capabilities[agent_id]
                logger.info(f"Unregistered capability {capability_name} for agent {agent_id}")
    
    async def get_capabilities(
        self, 
        agent_id: Optional[str] = None
    ) -> Dict[str, List[AgentCapability]]:
        """
        Get registered capabilities.
        
        Args:
            agent_id: Optional agent ID to filter capabilities
            
        Returns:
            Dict mapping agent IDs to their capabilities
        """
        async with self._lock:
            if agent_id:
                return {
                    agent_id: list(self._capabilities.get(agent_id, {}).values())
                }
            return {
                aid: list(caps.values()) 
                for aid, caps in self._capabilities.items()
            }
    
    async def request_capability(
        self, 
        capability_name: str, 
        params: Dict[str, Any],
        priority: int = 1
    ) -> Any:
        """
        Request a capability from any agent that provides it.
        
        Args:
            capability_name: Name of the capability
            params: Parameters for the capability
            priority: Priority level of the request
            
        Returns:
            Result from the capability handler
            
        Raises:
            ValueError: If no agent provides the capability
        """
        # Find agents with this capability
        providers = [
            agent_id
            for agent_id, capabilities in self._capabilities.items()
            if capability_name in capabilities
        ]
        
        if not providers:
            raise ValueError(f"No agent provides capability: {capability_name}")
        
        # TODO: Implement proper agent selection based on load, status, etc.
        selected_agent = providers[0]
        
        # TODO: Implement actual capability invocation
        return await self._invoke_capability(
            selected_agent, 
            capability_name, 
            params
        )
    
    async def _invoke_capability(
        self, 
        agent_id: str, 
        capability_name: str, 
        params: Dict[str, Any]
    ) -> Any:
        """
        Invoke a capability on an agent.
        
        Args:
            agent_id: ID of the agent
            capability_name: Name of the capability
            params: Parameters for the capability
            
        Returns:
            Result from the capability handler
        """
        # TODO: Implement actual agent communication
        pass
    
    async def publish_status(
        self, 
        agent_id: str, 
        status: str, 
        details: Dict[str, Any]
    ) -> None:
        """
        Update agent status.
        
        Args:
            agent_id: ID of the agent
            status: Status message
            details: Status details
        """
        async with self._lock:
            self._status[agent_id] = {
                "status": status,
                "details": details,
                "timestamp": datetime.now().isoformat()
            }
            
            # Notify subscribers
            if agent_id in self._subscribers:
                for subscriber_id in self._subscribers[agent_id]:
                    # TODO: Implement actual notification
                    pass
    
    async def subscribe(self, subscriber_id: str, agent_id: str) -> None:
        """
        Subscribe to status updates from an agent.
        
        Args:
            subscriber_id: ID of the subscribing agent
            agent_id: ID of the agent to subscribe to
        """
        async with self._lock:
            if agent_id not in self._subscribers:
                self._subscribers[agent_id] = set()
            self._subscribers[agent_id].add(subscriber_id)
    
    async def unsubscribe(self, subscriber_id: str, agent_id: str) -> None:
        """
        Unsubscribe from status updates from an agent.
        
        Args:
            subscriber_id: ID of the subscribing agent
            agent_id: ID of the agent to unsubscribe from
        """
        async with self._lock:
            if agent_id in self._subscribers:
                self._subscribers[agent_id].discard(subscriber_id)
                if not self._subscribers[agent_id]:
                    del self._subscribers[agent_id]
    
    async def subscribe_to_event(self, event_type: str) -> asyncio.Queue:
        """
        Subscribe to events of a specific type.
        
        Args:
            event_type: Type of event to subscribe to
            
        Returns:
            Queue for receiving events
        """
        queue = asyncio.Queue()
        self._event_subscribers[event_type].append(queue)
        return queue
    
    async def publish(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """
        Publish an event to all subscribers.
        
        Args:
            event_type: Type of event
            event_data: Event data
        """
        event = {
            "type": event_type,
            "data": event_data
        }
        for queue in self._event_subscribers[event_type]:
            await queue.put(event)
