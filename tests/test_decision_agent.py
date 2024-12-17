"""Tests for the decision agent implementation."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from src.agents.decision_agent import DecisionAgent
from src.agents.registry.v2 import AgentRegistry

@pytest.fixture
def mock_api_client():
    return AsyncMock()

@pytest.fixture
def mock_supabase():
    return AsyncMock()

@pytest.fixture
def mock_registry():
    registry = AsyncMock(spec=AgentRegistry)
    registry.get_capability = AsyncMock()
    return registry

@pytest.fixture
def decision_agent(mock_api_client, mock_supabase, mock_registry):
    return DecisionAgent(mock_api_client, mock_supabase, mock_registry)

@pytest.fixture
def sample_case():
    return {
        "_id": "test_case_123",
        "title": "Test Security Incident",
        "severity": "medium",
        "created_at": 1639900800000,  # Example timestamp
        "status": "new"
    }

@pytest.fixture
def sample_analysis():
    return {
        "risk_level": 8,
        "needs_human": True,
        "risk_factors": ["suspicious_ip", "multiple_failed_logins", "unusual_time"],
        "recommendations": ["manual_review", "auto_block_ip", "manual_contact_user"]
    }

@pytest.mark.asyncio
async def test_analyze_and_decide_high_risk(decision_agent, sample_case, sample_analysis, mock_registry):
    # Setup
    analyze_capability = AsyncMock(return_value=sample_analysis)
    investigate_capability = AsyncMock(return_value={"investigation_details": "test"})
    mock_registry.get_capability.side_effect = [analyze_capability, investigate_capability]

    # Execute
    decisions = await decision_agent.analyze_and_decide(sample_case)

    # Verify
    assert decisions["needs_investigation"] == True
    assert decisions["priority"] >= 8
    assert "manual_review" in decisions["required_human_actions"]
    assert "auto_block_ip" in decisions["automated_actions"]
    mock_registry.get_capability.assert_any_call("analyze_case")
    mock_registry.get_capability.assert_any_call("investigate_case")

@pytest.mark.asyncio
async def test_analyze_and_decide_low_risk(decision_agent, sample_case, mock_registry):
    # Setup
    low_risk_analysis = {
        "risk_level": 2,
        "needs_human": False,
        "risk_factors": ["routine_access"],
        "recommendations": ["auto_close"]
    }
    analyze_capability = AsyncMock(return_value=low_risk_analysis)
    mock_registry.get_capability.return_value = analyze_capability

    # Execute
    decisions = await decision_agent.analyze_and_decide(sample_case)

    # Verify
    assert decisions["needs_investigation"] == False
    assert decisions["priority"] <= 3
    assert "auto_close" in decisions["automated_actions"]
    assert len(decisions["required_human_actions"]) == 0
    mock_registry.get_capability.assert_called_once_with("analyze_case")

@pytest.mark.asyncio
async def test_analyze_and_decide_medium_risk(decision_agent, sample_case, mock_registry):
    # Setup
    medium_risk_analysis = {
        "risk_level": 5,
        "needs_human": False,
        "risk_factors": ["failed_login"],
        "recommendations": ["auto_monitor"]
    }
    analyze_capability = AsyncMock(return_value=medium_risk_analysis)
    mock_registry.get_capability.return_value = analyze_capability

    # Execute
    decisions = await decision_agent.analyze_and_decide(sample_case)

    # Verify
    assert decisions["needs_investigation"] == False
    assert 3 < decisions["priority"] <= 7
    assert "auto_monitor" in decisions["automated_actions"]
    mock_registry.get_capability.assert_called_once_with("analyze_case")

@pytest.mark.asyncio
async def test_record_decision_metrics(decision_agent, mock_supabase):
    # Setup
    case_id = "test_case_123"
    decisions = {
        "priority": 8,
        "needs_investigation": True,
        "automated_actions": ["auto_block_ip"],
        "required_human_actions": ["manual_review"]
    }

    # Execute
    await decision_agent._record_decision_metrics(case_id, decisions)

    # Verify
    mock_supabase.insert.assert_called_once()
    call_args = mock_supabase.insert.call_args[0]
    assert call_args[0] == "decision_metrics"
    metrics = call_args[1]
    assert metrics["case_id"] == case_id
    assert metrics["priority"] == 8
    assert metrics["needs_investigation"] == True
    assert metrics["automated_actions_count"] == 1
    assert metrics["required_human_actions_count"] == 1

@pytest.mark.asyncio
async def test_analyze_and_decide_error_handling(decision_agent, sample_case, mock_registry):
    # Setup
    analyze_capability = AsyncMock(side_effect=Exception("Analysis failed"))
    mock_registry.get_capability.return_value = analyze_capability

    # Execute and verify
    with pytest.raises(Exception) as exc_info:
        await decision_agent.analyze_and_decide(sample_case)
    assert str(exc_info.value) == "Analysis failed"
