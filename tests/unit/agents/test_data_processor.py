"""
Unit tests for the data processor agent.
"""
import pytest
from typing import Dict, Any

from src.agents.specialized import DataProcessorAgent
from src.agents.registry import AgentRegistry
from src.utils.retry import RetryConfig

@pytest.fixture
def registry():
    """Provide a test agent registry."""
    return AgentRegistry()

@pytest.fixture
async def agent(registry):
    """Provide a test data processor agent."""
    agent = DataProcessorAgent(
        registry,
        error_rate=0.0,  # Disable random errors for testing
        processing_time=0.0,  # No processing delay for testing
        retry_config=RetryConfig(max_retries=1)
    )
    await agent.initialize()
    return agent

@pytest.mark.asyncio
async def test_initialize_capabilities(agent: DataProcessorAgent):
    """Test capability initialization."""
    capabilities = await agent.registry.get_capabilities(agent.agent_id)
    
    assert len(capabilities[agent.agent_id]) == 1
    capability = capabilities[agent.agent_id][0]
    assert capability.name == "process_data"
    assert "data" in capability.parameters

@pytest.mark.asyncio
async def test_process_data_uppercase(agent: DataProcessorAgent):
    """Test uppercase data processing."""
    request_data = {
        "params": {
            "data": "test data",
            "transform_type": "uppercase"
        }
    }
    
    result = await agent._process_capability_request(request_data)
    assert result == "TEST DATA"

@pytest.mark.asyncio
async def test_process_data_lowercase(agent: DataProcessorAgent):
    """Test lowercase data processing."""
    request_data = {
        "params": {
            "data": "TEST DATA",
            "transform_type": "lowercase"
        }
    }
    
    result = await agent._process_capability_request(request_data)
    assert result == "test data"

@pytest.mark.asyncio
async def test_process_data_reverse(agent: DataProcessorAgent):
    """Test reverse data processing."""
    request_data = {
        "params": {
            "data": "test data",
            "transform_type": "reverse"
        }
    }
    
    result = await agent._process_capability_request(request_data)
    assert result == "atad tset"

@pytest.mark.asyncio
async def test_process_data_no_data(agent: DataProcessorAgent):
    """Test error handling for missing data."""
    request_data = {
        "params": {}
    }
    
    with pytest.raises(ValueError, match="No data provided"):
        await agent._process_capability_request(request_data)

@pytest.mark.asyncio
async def test_process_data_with_retry(registry: AgentRegistry):
    """Test processing with retry behavior."""
    agent = DataProcessorAgent(
        registry,
        error_rate=1.0,  # Always fail first attempt
        processing_time=0.0,
        retry_config=RetryConfig(
            max_retries=2,
            initial_delay=0.1
        )
    )
    await agent.initialize()
    
    request_data = {
        "params": {
            "data": "test data",
            "transform_type": "uppercase"
        },
        "retry_count": 0
    }
    
    with pytest.raises(Exception, match="Random processing error"):
        await agent._process_capability_request(request_data)
