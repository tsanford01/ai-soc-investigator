"""Tests for error handling and retry mechanisms across the system."""

import pytest
import asyncio
from unittest.mock import patch, MagicMock
from coordinator_agent import CoordinatorAgent
from ai_agent import AIAgent
from supabase_client import SupabaseClient

@pytest.fixture
def mock_supabase():
    """Create a mock Supabase client."""
    client = MagicMock(spec=SupabaseClient)
    return client

@pytest.fixture
def mock_ai_agent():
    """Create a mock AI agent."""
    agent = MagicMock(spec=AIAgent)
    return agent

@pytest.fixture
async def coordinator(mock_supabase, mock_ai_agent):
    """Create a coordinator agent with mocked dependencies."""
    agent = CoordinatorAgent(
        supabase_client=mock_supabase,
        ai_agent=mock_ai_agent
    )
    return agent

@pytest.mark.asyncio
async def test_retry_on_transient_failure(coordinator, mock_ai_agent):
    """Test that operations are retried on transient failures."""
    # Setup mock to fail twice then succeed
    mock_ai_agent.analyze_case.side_effect = [
        Exception("Temporary failure"),
        Exception("Temporary failure"),
        {"decision": "approve", "confidence": 0.95}
    ]
    
    result = await coordinator.process_case({"id": "test-case-1"})
    
    assert result is not None
    assert mock_ai_agent.analyze_case.call_count == 3

@pytest.mark.asyncio
async def test_graceful_degradation(coordinator, mock_ai_agent):
    """Test system degrades gracefully when service is unavailable."""
    mock_ai_agent.analyze_case.side_effect = Exception("Service unavailable")
    
    result = await coordinator.process_case({"id": "test-case-2"})
    
    assert result is not None
    assert result.get("status") == "manual_review"
    assert result.get("error") is not None

@pytest.mark.asyncio
async def test_concurrent_case_processing(coordinator):
    """Test that multiple cases can be processed concurrently."""
    test_cases = [
        {"id": f"test-case-{i}"} for i in range(5)
    ]
    
    tasks = [
        coordinator.process_case(case)
        for case in test_cases
    ]
    
    results = await asyncio.gather(*tasks)
    assert len(results) == len(test_cases)

@pytest.mark.asyncio
async def test_timeout_handling(coordinator):
    """Test that long-running operations are properly timed out."""
    async def slow_operation():
        await asyncio.sleep(2)
        return {"result": "too late"}
    
    with patch.object(coordinator, 'process_case', side_effect=slow_operation):
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(
                coordinator.process_case({"id": "test-case-slow"}),
                timeout=1
            )

@pytest.mark.asyncio
async def test_transaction_rollback(coordinator, mock_supabase):
    """Test that database transactions are rolled back on failure."""
    mock_supabase.begin_transaction.return_value = MagicMock()
    mock_supabase.execute_query.side_effect = Exception("Database error")
    
    with pytest.raises(Exception):
        await coordinator.process_case({"id": "test-case-db-error"})
    
    mock_supabase.rollback_transaction.assert_called_once()

@pytest.mark.asyncio
async def test_performance_metrics(coordinator):
    """Test that performance metrics are properly tracked."""
    result = await coordinator.process_case({"id": "test-case-metrics"})
    
    assert "execution_time" in result
    assert "retry_count" in result
    assert isinstance(result["execution_time"], float)
    assert isinstance(result["retry_count"], int)
