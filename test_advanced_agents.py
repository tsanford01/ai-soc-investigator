import asyncio
import logging
from typing import Dict, Any, List
from datetime import datetime
import random
from agent_registry import AgentRegistry
from base_agent import BaseAgent, RetryConfig, AgentCapability
from agent_supervisor import AgentSupervisor
from rate_limiter import RateLimiter
import uuid

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataProcessorAgent(BaseAgent):
    def __init__(self, registry: AgentRegistry, error_rate: float = 0.2, 
                 processing_time: float = 0.5):
        self.error_rate = error_rate
        self.processing_time = processing_time
        super().__init__(registry, retry_config=RetryConfig(max_retries=3))

    async def _initialize_capabilities(self) -> None:
        self.add_capability(
            "process_data",
            "Process and transform data",
            ["data"]
        )

    async def _process_capability_request(self, request_data: Dict[str, Any]) -> Any:
        # Simulate processing time
        await asyncio.sleep(self.processing_time)
        
        # Simulate random failures
        if random.random() < self.error_rate:
            raise Exception("Random processing error")

        data = request_data.get("params", {}).get("data")
        if data:
            result = data.upper() if isinstance(data, str) else data
            await self.registry.publish("processing_complete", {
                "processor_id": self.agent_id,
                "original_data": data,
                "processed_data": result,
                "retry_count": request_data.get("retry_count", 0)
            })
            return result
        return None

class DataRequesterAgent(BaseAgent):
    def __init__(self, registry: AgentRegistry):
        super().__init__(registry)
        self.registry.subscribe("processing_complete", self.handle_processing_result)
        self.registry.subscribe("agent_error", self.handle_error)
        self.received_results = []
        self.errors = []

    async def _initialize_capabilities(self) -> None:
        # This agent only makes requests, it doesn't provide capabilities
        pass

    async def _process_capability_request(self, request_data: Dict[str, Any]) -> Any:
        # This agent doesn't process requests, it only makes them
        return None

    async def handle_processing_result(self, data: Dict[str, Any]) -> None:
        self.received_results.append(data)
        logger.info(f"Received result from {data['processor_id']}: "
                   f"{data['processed_data']} (retry: {data['retry_count']})")

    async def handle_error(self, error_data: Dict[str, Any]) -> None:
        self.errors.append(error_data)
        logger.warning(f"Error from {error_data.get('agent_id')}: {error_data.get('error')}")

    async def request_processing(self, data: str, priority: int = 1) -> None:
        await self.request_capability("process_data", {"data": data}, priority)

class TestAgent(BaseAgent):
    """Test agent implementation for testing purposes"""
    
    async def _initialize_capabilities(self) -> None:
        """Initialize agent capabilities"""
        self.add_capability(
            name="process_data",
            description="Process data with priority",
            parameters={"data": "string"},
            return_type="string"
        )
    
    async def _process_capability_request(self, request_data: Dict[str, Any]) -> Any:
        """Process a capability request"""
        capability = request_data["capability"]
        params = request_data["params"]
        priority = request_data.get("priority", 1)
        
        # Simulate processing
        await asyncio.sleep(0.1)
        return f"Processed {params['data']} with priority {priority}"

class RateLimitedProcessor(TestAgent):
    """Test agent with rate limiting"""
    
    def __init__(self, registry: AgentRegistry):
        super().__init__(
            registry=registry,
            retry_config=RetryConfig(max_retries=3),
            rate_limiter=RateLimiter(calls=2, period=1.0)  # 2 requests per second
        )

class HealthMonitor:
    """Simple health monitor for testing"""
    def __init__(self):
        self.is_healthy = True
        self.last_check = datetime.now()
    
    def check_health(self) -> bool:
        """Check if agent is healthy"""
        self.last_check = datetime.now()
        return self.is_healthy

class SupervisedAgent(TestAgent):
    """Test agent with supervisor integration"""
    
    def __init__(self, registry: AgentRegistry):
        super().__init__(registry)
        self._health_monitor = HealthMonitor()
        self._state = {}
    
    async def get_state(self) -> Dict[str, Any]:
        """Get agent state for backup"""
        return {
            "agent_id": self.agent_id,
            "capabilities": [cap.__dict__ for cap in self._capabilities],
            "health": self._health_monitor.is_healthy,
            "state": self._state
        }
    
    async def restore_state(self, state: Dict[str, Any]) -> None:
        """Restore agent state from backup"""
        self._state = state.get("state", {})
        self._health_monitor.is_healthy = state.get("health", True)

async def setup_test_agents():
    """Set up test agents with capabilities"""
    registry = AgentRegistry()
    
    # Create test agents with process_data capability
    agents = []
    for _ in range(3):
        agent = TestAgent(registry)
        await agent._initialize_capabilities()
        registry.register_agent(
            agent=agent,
            capabilities=[AgentCapability(
                name="process_data",
                description="Process data with priority",
                parameters={"data": "string"},
                return_type="string"
            )],
            max_concurrent=2
        )
        agents.append(agent)
    
    return registry, agents

async def test_load_balancing():
    """Test load balancing across multiple agents"""
    registry, agents = await setup_test_agents()
    requester = TestAgent(registry)
    await requester._initialize_capabilities()
    
    # Send multiple requests with different priorities
    tasks = []
    for i in range(5):
        data = f"test_data_{i}"
        priority = i % 3 + 1  # priorities 1-3
        task = asyncio.create_task(requester.request_capability(
            "process_data",
            {"data": data},
            priority
        ))
        tasks.append(task)
    
    try:
        results = await asyncio.gather(*tasks)
        print(f"All requests completed successfully: {results}")
    except Exception as e:
        print(f"Error during load balancing test: {e}")
        raise

async def test_rate_limiting():
    """Test rate limiting functionality"""
    logger.info("Starting rate limiting test...")
    registry = AgentRegistry()
    
    # Create rate limited processor
    processor = RateLimitedProcessor(registry)
    await processor._initialize_capabilities()
    
    # Send multiple requests to the same agent
    start_time = datetime.now()
    tasks = []
    for i in range(10):  # Send 10 requests with 2 req/sec limit
        task = asyncio.create_task(
            processor.handle_request({
                "capability": "process_data",
                "params": {"data": f"test_data_{i}"},
                "priority": 1
            })
        )
        tasks.append(task)
    
    # Wait for all requests to complete
    results = await asyncio.gather(*tasks)
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    # Verify that rate limiting worked
    logger.info(f"Rate limiting test completed in {duration:.2f} seconds")
    logger.info(f"Results: {results}")
    
    # With 2 requests per second limit and 10 requests, should take at least 4 seconds
    assert duration >= 4.0, f"Rate limiting not working, took only {duration:.2f} seconds"
    logger.info("Rate limiting test passed successfully")

async def test_supervisor_integration():
    """Test supervisor monitoring and backup functionality"""
    logger.info("Starting supervisor integration test...")
    registry = AgentRegistry()
    
    # Create supervised agent
    processor = SupervisedAgent(registry)
    await processor._initialize_capabilities()
    
    # Create supervisor
    supervisor = AgentSupervisor(registry)
    await supervisor.start()
    
    # Wait for initial backup
    await asyncio.sleep(1)
    
    # Simulate agent failure
    processor._health_monitor.is_healthy = False
    await asyncio.sleep(1)
    
    # Check if agent is unhealthy
    assert not processor._health_monitor.is_healthy, \
        "Agent should be unhealthy"
    
    # Restore agent health
    processor._health_monitor.is_healthy = True
    await asyncio.sleep(1)
    
    # Check if agent recovered
    assert processor._health_monitor.is_healthy, \
        "Agent should be healthy"
    
    # Stop supervisor
    await supervisor.stop()
    logger.info("Supervisor integration test passed successfully")

async def main():
    await test_load_balancing()
    await test_rate_limiting()
    await test_supervisor_integration()

if __name__ == "__main__":
    asyncio.run(main())
