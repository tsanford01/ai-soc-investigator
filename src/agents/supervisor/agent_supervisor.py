"""
Agent supervisor for monitoring and managing agent health.
"""
from typing import Dict, Any, Optional, List
import logging
import asyncio
from datetime import datetime, timedelta

from ..registry import AgentRegistry
from ...config.settings import Settings

logger = logging.getLogger(__name__)

class AgentSupervisor:
    """
    Supervisor for monitoring and managing agent health.
    
    Features:
    - Health monitoring
    - Automatic recovery
    - Performance tracking
    - State backup and restore
    """
    
    def __init__(
        self, 
        registry: AgentRegistry,
        settings: Settings,
        health_check_interval: float = 60.0,
        backup_interval: float = 300.0
    ):
        """
        Initialize agent supervisor.
        
        Args:
            registry: Agent registry
            settings: Application settings
            health_check_interval: Interval between health checks in seconds
            backup_interval: Interval between state backups in seconds
        """
        self.registry = registry
        self.settings = settings
        self.health_check_interval = health_check_interval
        self.backup_interval = backup_interval
        self._agent_states: Dict[str, Dict[str, Any]] = {}
        self._last_health_check: Dict[str, datetime] = {}
        self._last_backup: Dict[str, datetime] = {}
        self._running = False
        self._tasks: List[asyncio.Task] = []
    
    async def start(self) -> None:
        """Start the supervisor."""
        if self._running:
            return
            
        self._running = True
        self._tasks = [
            asyncio.create_task(self._health_check_loop()),
            asyncio.create_task(self._backup_loop())
        ]
        
        logger.info("Agent supervisor started")
    
    async def stop(self) -> None:
        """Stop the supervisor."""
        self._running = False
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks = []
        
        logger.info("Agent supervisor stopped")
    
    async def _health_check_loop(self) -> None:
        """Run periodic health checks."""
        while self._running:
            try:
                await self._check_all_agents()
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
            
            await asyncio.sleep(self.health_check_interval)
    
    async def _backup_loop(self) -> None:
        """Run periodic state backups."""
        while self._running:
            try:
                await self._backup_all_agents()
            except Exception as e:
                logger.error(f"Error in backup loop: {e}")
            
            await asyncio.sleep(self.backup_interval)
    
    async def _check_all_agents(self) -> None:
        """Check health of all registered agents."""
        capabilities = await self.registry.get_capabilities()
        
        for agent_id in capabilities:
            try:
                await self._check_agent_health(agent_id)
            except Exception as e:
                logger.error(f"Error checking agent {agent_id}: {e}")
    
    async def _check_agent_health(self, agent_id: str) -> None:
        """
        Check health of a specific agent.
        
        Args:
            agent_id: ID of the agent to check
        """
        # Get agent metrics
        metrics = await self.registry.request_capability(
            "get_metrics",
            {"agent_id": agent_id}
        )
        
        # Check for problems
        if self._detect_health_issues(metrics):
            await self._handle_unhealthy_agent(agent_id)
        
        self._last_health_check[agent_id] = datetime.now()
    
    def _detect_health_issues(self, metrics: Dict[str, Any]) -> bool:
        """
        Detect health issues from metrics.
        
        Args:
            metrics: Agent metrics
            
        Returns:
            bool: True if issues detected
        """
        # Example health checks
        error_rate = metrics.get("errors", 0) / max(metrics.get("requests", 1), 1)
        avg_duration = metrics.get("avg_duration", 0)
        
        return (
            error_rate > 0.5 or  # More than 50% errors
            avg_duration > 10.0   # Requests taking too long
        )
    
    async def _handle_unhealthy_agent(self, agent_id: str) -> None:
        """
        Handle an unhealthy agent.
        
        Args:
            agent_id: ID of the unhealthy agent
        """
        logger.warning(f"Agent {agent_id} is unhealthy")
        
        # Try to restore from last known good state
        if agent_id in self._agent_states:
            await self._restore_agent_state(agent_id)
        
        # Notify about the issue
        await self.registry.publish_status(
            "supervisor",
            "agent_unhealthy",
            {"agent_id": agent_id}
        )
    
    async def _backup_all_agents(self) -> None:
        """Backup state of all registered agents."""
        capabilities = await self.registry.get_capabilities()
        
        for agent_id in capabilities:
            try:
                await self._backup_agent_state(agent_id)
            except Exception as e:
                logger.error(f"Error backing up agent {agent_id}: {e}")
    
    async def _backup_agent_state(self, agent_id: str) -> None:
        """
        Backup state of a specific agent.
        
        Args:
            agent_id: ID of the agent to backup
        """
        # Get agent state
        state = await self.registry.request_capability(
            "get_state",
            {"agent_id": agent_id}
        )
        
        self._agent_states[agent_id] = state
        self._last_backup[agent_id] = datetime.now()
        
        logger.debug(f"Backed up state for agent {agent_id}")
    
    async def _restore_agent_state(self, agent_id: str) -> None:
        """
        Restore state of a specific agent.
        
        Args:
            agent_id: ID of the agent to restore
        """
        if agent_id not in self._agent_states:
            return
            
        state = self._agent_states[agent_id]
        
        # Restore agent state
        await self.registry.request_capability(
            "restore_state",
            {
                "agent_id": agent_id,
                "state": state
            }
        )
        
        logger.info(f"Restored state for agent {agent_id}")
    
    def get_agent_status(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status information for an agent.
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            Optional[Dict[str, Any]]: Agent status information
        """
        return {
            "last_health_check": self._last_health_check.get(agent_id),
            "last_backup": self._last_backup.get(agent_id),
            "has_backup": agent_id in self._agent_states
        }
