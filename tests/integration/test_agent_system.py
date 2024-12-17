"""Integration tests for the agent system."""
import asyncio
import uuid
import pytest
from typing import Dict, Any

from src.config.settings import load_settings
from src.agents.registry import AgentRegistry
from src.agents.specialized import DataProcessorAgent
from src.utils.retry import RetryConfig

@pytest.fixture
def settings():
    """Load application settings."""
    return load_settings()

@pytest.fixture
def registry():
    """Create agent registry."""
    return AgentRegistry()

@pytest.fixture
async def agent(registry):
    """Create and initialize data processor agent."""
    agent = DataProcessorAgent(
        registry,
        error_rate=0.0,  # No errors for integration test
        processing_time=0.1,  # Small delay to simulate work
        retry_config=RetryConfig(max_retries=2, initial_delay=0.1)
    )
    await agent.initialize()
    return agent

async def process_and_verify(
    agent: DataProcessorAgent,
    data: str,
    transform_type: str,
    expected_result: str,
    correlation_id: str = None
):
    """Helper to process data and verify results."""
    correlation_id = correlation_id or str(uuid.uuid4())
    request_data = {
        "params": {
            "data": data,
            "transform_type": transform_type,
            "correlation_id": correlation_id
        }
    }
    
    # Subscribe to processing events with correlation ID filter
    event_queue = await agent.registry.subscribe_to_event("processing_complete")
    
    # Process the data
    result = await agent._process_capability_request(request_data)
    assert result == expected_result
    
    # Keep getting events until we find our correlated event
    while True:
        event = await event_queue.get()
        if event["data"].get("correlation_id") == correlation_id:
            assert event["type"] == "processing_complete"
            assert event["data"]["processed_data"] == expected_result
            assert event["data"]["original_data"] == data
            assert event["data"]["transform_type"] == transform_type
            break

@pytest.mark.asyncio
async def test_agent_system_integration(settings, agent):
    """Test the agent system with various transformations."""
    # Test uppercase transformation
    await process_and_verify(
        agent,
        "hello world",
        "uppercase",
        "HELLO WORLD",
        correlation_id="test1"
    )
    
    # Test lowercase transformation
    await process_and_verify(
        agent,
        "HELLO WORLD",
        "lowercase",
        "hello world",
        correlation_id="test2"
    )
    
    # Test reverse transformation
    await process_and_verify(
        agent,
        "hello world",
        "reverse",
        "dlrow olleh",
        correlation_id="test3"
    )

@pytest.mark.asyncio
async def test_retry_behavior(registry):
    """Test retry behavior with high error rate."""
    # Create agent with 100% error rate
    agent = DataProcessorAgent(
        registry,
        error_rate=1.0,  # Always fail first attempt
        processing_time=0.1,
        retry_config=RetryConfig(max_retries=3, initial_delay=0.1)
    )
    await agent.initialize()
    
    request_data = {
        "params": {
            "data": "test data",
            "transform_type": "uppercase",
            "correlation_id": "retry-test"
        }
    }
    
    # Should fail after max retries
    with pytest.raises(Exception, match="Random processing error"):
        await agent._process_capability_request(request_data)

@pytest.mark.asyncio
async def test_concurrent_processing(registry):
    """Test concurrent processing of multiple requests."""
    agent = DataProcessorAgent(
        registry,
        error_rate=0.0,  # No errors for concurrent test
        processing_time=0.1,
        retry_config=RetryConfig(max_retries=1)
    )
    await agent.initialize()
    
    # Create multiple concurrent requests with unique correlation IDs
    requests = [
        ("hello", "uppercase", "HELLO", "concurrent1"),
        ("WORLD", "lowercase", "world", "concurrent2"),
        ("test", "reverse", "tset", "concurrent3")
    ]
    
    # Process requests concurrently
    tasks = [
        process_and_verify(agent, data, transform_type, expected, correlation_id)
        for data, transform_type, expected, correlation_id in requests
    ]
    
    await asyncio.gather(*tasks)
