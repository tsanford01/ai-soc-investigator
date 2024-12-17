"""Test script for case processing functionality."""
import asyncio
import logging
from datetime import datetime, timedelta
import os
import tempfile
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.clients.api_client import APIClient
from src.clients.auth import AuthManager
from src.clients.supabase_client import SupabaseClient
from scripts.process_cases import CaseProcessor
from src.agents.decision_agent import DecisionAgent

# Set up logging to both file and console
temp_dir = tempfile.gettempdir()
log_file = os.path.join(temp_dir, 'test_case_processing.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
logger.info(f"Logging to: {log_file}")

@pytest.fixture
def mock_api_client():
    client = AsyncMock(spec=APIClient)
    # Add required methods
    client.update_case_status = AsyncMock()
    client.get_case_alerts = AsyncMock(return_value=[])
    client.get_case_observables = AsyncMock(return_value=[])
    client.get_case_activities = AsyncMock(return_value={"data": []})
    return client

@pytest.fixture
def mock_supabase():
    client = AsyncMock(spec=SupabaseClient)
    # Add required methods
    client.update = AsyncMock()
    client.upsert_alert_data = AsyncMock()
    client.upsert_observable_data = AsyncMock()
    client.upsert_activity_data = AsyncMock()
    return client

@pytest.fixture
def mock_decision_agent():
    return AsyncMock(spec=DecisionAgent)

@pytest.fixture
def case_processor(mock_api_client, mock_supabase, mock_decision_agent):
    processor = CaseProcessor(mock_api_client, mock_supabase)
    processor.decision_agent = mock_decision_agent
    # Mock only the data processing methods
    processor.process_case_alerts = AsyncMock()
    processor.process_case_observables = AsyncMock()
    processor.process_case_activities = AsyncMock()
    return processor

@pytest.fixture
def sample_case():
    return {
        "_id": "test_case_123",
        "case_data": "test case data"
    }

@pytest.fixture
def sample_decisions():
    return {
        "needs_investigation": True,
        "priority": 8,
        "automated_actions": ["auto_monitor"],
        "required_human_actions": ["manual_review"],
        "investigation": {"details": "test investigation"}
    }

async def test_case_processing():
    """Test the case processing functionality."""
    try:
        # Initialize clients
        auth_manager = AuthManager()
        api_client = APIClient(auth_manager)
        supabase_client = SupabaseClient()
        
        # Create processor with small batch size
        processor = CaseProcessor(api_client, supabase_client)
        
        # Process a small batch of cases
        await processor.process_cases(limit=2)
        
        logger.info("Test completed successfully")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise

@pytest.mark.asyncio
@patch.object(CaseProcessor, '_update_case_status')
@patch.object(CaseProcessor, '_monitor_case')
@patch.object(CaseProcessor, '_auto_close_case')
async def test_process_single_case_high_risk(mock_auto_close, mock_monitor, mock_update_status, 
                                           case_processor, sample_case, sample_decisions, mock_decision_agent):
    # Setup
    mock_decision_agent.analyze_and_decide.return_value = sample_decisions
    mock_auto_close.return_value = None
    mock_monitor.return_value = None
    mock_update_status.return_value = None

    # Execute
    await case_processor.process_single_case(sample_case)

    # Verify
    mock_decision_agent.analyze_and_decide.assert_called_once_with(sample_case)
    case_processor.process_case_alerts.assert_called_once()
    case_processor.process_case_observables.assert_called_once()
    case_processor.process_case_activities.assert_called_once()
    mock_update_status.assert_called_once_with(sample_case["_id"], sample_decisions)

@pytest.mark.asyncio
@patch.object(CaseProcessor, '_update_case_status')
@patch.object(CaseProcessor, '_monitor_case')
@patch.object(CaseProcessor, '_auto_close_case')
async def test_process_single_case_auto_close(mock_auto_close, mock_monitor, mock_update_status,
                                            case_processor, sample_case, mock_decision_agent):
    # Setup
    low_risk_decisions = {
        "needs_investigation": False,
        "priority": 2,
        "automated_actions": ["auto_close"],
        "required_human_actions": []
    }
    mock_decision_agent.analyze_and_decide.return_value = low_risk_decisions
    mock_auto_close.return_value = None
    mock_monitor.return_value = None
    mock_update_status.return_value = None

    # Execute
    await case_processor.process_single_case(sample_case)

    # Verify
    mock_auto_close.assert_called_once_with(sample_case["_id"])
    case_processor.process_case_activities.assert_not_called()

@pytest.mark.asyncio
@patch.object(CaseProcessor, '_update_case_status')
@patch.object(CaseProcessor, '_monitor_case')
@patch.object(CaseProcessor, '_auto_close_case')
async def test_process_single_case_auto_monitor(mock_auto_close, mock_monitor, mock_update_status,
                                              case_processor, sample_case, mock_decision_agent):
    # Setup
    medium_risk_decisions = {
        "needs_investigation": False,
        "priority": 5,
        "automated_actions": ["auto_monitor"],
        "required_human_actions": []
    }
    mock_decision_agent.analyze_and_decide.return_value = medium_risk_decisions
    mock_auto_close.return_value = None
    mock_monitor.return_value = None
    mock_update_status.return_value = None

    # Execute
    await case_processor.process_single_case(sample_case)

    # Verify
    mock_monitor.assert_called_once_with(sample_case["_id"])
    case_processor.process_case_alerts.assert_called_once()
    case_processor.process_case_observables.assert_called_once()
    case_processor.process_case_activities.assert_not_called()

@pytest.mark.asyncio
async def test_auto_close_case(mock_api_client):
    # Setup
    case_id = "test_case_123"
    processor = CaseProcessor(mock_api_client, AsyncMock())

    # Execute
    await processor._auto_close_case(case_id)

    # Verify
    mock_api_client.update_case_status.assert_called_once_with(case_id, "closed")

@pytest.mark.asyncio
async def test_monitor_case(mock_api_client):
    # Setup
    case_id = "test_case_123"
    processor = CaseProcessor(mock_api_client, AsyncMock())

    # Execute
    await processor._monitor_case(case_id)

    # Verify
    mock_api_client.update_case_status.assert_called_once_with(case_id, "monitoring")

@pytest.mark.asyncio
async def test_update_case_status(mock_supabase):
    # Setup
    case_id = "test_case_123"
    processor = CaseProcessor(AsyncMock(), mock_supabase)
    decisions = {
        "needs_investigation": True,
        "priority": 8,
        "automated_actions": ["auto_monitor"],
        "required_human_actions": ["manual_review"]
    }

    # Execute
    await processor._update_case_status(case_id, decisions)

    # Verify
    mock_supabase.update.assert_called_once_with(
        "cases",
        {"case_id": case_id},
        {
            "priority": decisions["priority"],
            "needs_investigation": decisions["needs_investigation"],
            "automated_actions": decisions["automated_actions"],
            "required_human_actions": decisions["required_human_actions"]
        }
    )

if __name__ == "__main__":
    asyncio.run(test_case_processing())
