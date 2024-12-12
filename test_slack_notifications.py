import asyncio
import os
from dotenv import load_dotenv
from api_client import APIClient
from supabase_client import SupabaseWrapper
from ai_agent import AIAgent
from case_collector import CaseCollector
from auth import AuthManager
from unittest.mock import MagicMock

def create_mock_api_client():
    mock_client = MagicMock()
    
    # Mock get_case response
    mock_client.get_case.return_value = {
        '_id': 'TEST-001',
        'name': 'Test High Priority Case',
        'severity': 'Critical',
        'status': 'Open',
        'score': 95,
        'size': 'Large',
        'created_by': 'test_user',
        'modified_by': 'test_user',
        'tenant_name': 'test_tenant'
    }
    
    # Mock get_case_summary response
    mock_client.get_case_summary.return_value = "Critical security incident detected with multiple indicators of compromise."
    
    # Mock get_case_alerts response
    mock_client.get_case_alerts.return_value = {
        'items': [
            {
                '_id': 'ALERT-001',
                'name': 'Suspicious Data Exfiltration',
                'severity': 'High',
                'details': {
                    'source_ip': '192.168.1.100',
                    'destination_ip': '203.0.113.100',
                    'bytes_transferred': 50000000
                }
            }
        ]
    }
    
    # Mock get_case_activities response
    mock_client.get_case_activities.return_value = {
        'items': [
            {
                'type': 'system',
                'description': 'Large data transfer detected',
                'timestamp': '2024-12-12T09:00:00Z'
            }
        ]
    }
    
    return mock_client

async def test_high_priority_notification():
    # Initialize components with mock API client
    auth_manager = AuthManager()
    api_client = create_mock_api_client()
    supabase_client = SupabaseWrapper()
    ai_agent = AIAgent()
    case_collector = CaseCollector(api_client, supabase_client, ai_agent)
    
    # Test case ID
    test_case_id = 'TEST-001'
    
    # Process the case (this will trigger AI analysis and notification)
    try:
        result = case_collector.collect_case_data(test_case_id)
        print(f"Test case processed successfully: {result}")
        print("Check the Slack channel for notification.")
    except Exception as e:
        print(f"Error during test: {str(e)}")

if __name__ == "__main__":
    load_dotenv()
    asyncio.run(test_high_priority_notification())
