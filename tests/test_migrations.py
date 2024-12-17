import os
import pytest
from typing import Dict, Any
from dotenv import load_dotenv
from supabase import create_client, Client
import json
import time

# Load environment variables
load_dotenv()

@pytest.fixture
def supabase_client() -> Client:
    """Create a Supabase client for testing.
    
    Returns:
        Client: Configured Supabase client
    
    Raises:
        pytest.skip: If credentials are not configured
    """
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        pytest.skip("Supabase credentials not configured")
    return create_client(url, key)

@pytest.fixture
def test_case() -> Dict[str, Any]:
    """Create a test case with required fields.
    
    Returns:
        Dict[str, Any]: Test case data
    """
    return {
        "external_id": f"TEST-{int(time.time())}",
        "title": "Test Case",
        "severity": "High",
        "status": "Open",
        "summary": "Test case summary",
        "metadata": {"source": "test"},
        "tenant_name": "Test Tenant",
        "score": 80,
        "size": 100
    }

def test_insert_and_query_cases(supabase_client: Client, test_case: Dict[str, Any]) -> None:
    """Test case table operations.
    
    Args:
        supabase_client: Supabase client fixture
        test_case: Test case data fixture
    
    Raises:
        AssertionError: If any test assertions fail
        Exception: If database operations fail
    """
    # Check table structure
    try:
        result = supabase_client.table("cases").select("*").limit(1).execute()
        columns = result.data[0].keys() if result.data else []
        required_columns = {"external_id", "title", "severity", "status", "summary"}
        assert all(col in columns for col in required_columns), f"Missing required columns. Found: {columns}"
    except Exception as e:
        pytest.fail(f"Error checking cases table structure: {str(e)}")
    
    # Insert test case
    try:
        result = supabase_client.table("cases").insert(test_case).execute()
        assert result.data is not None, "Failed to insert test case"
        inserted_case = result.data[0]
        for key, value in test_case.items():
            assert inserted_case[key] == value, f"Case field mismatch: {key}"
    except Exception as e:
        pytest.fail(f"Error inserting case: {str(e)}")
    
    # Query test case
    try:
        result = supabase_client.table("cases").select("*").eq("external_id", test_case["external_id"]).execute()
        assert result.data is not None and len(result.data) == 1, "Failed to query case"
        queried_case = result.data[0]
        for key, value in test_case.items():
            assert queried_case[key] == value, f"Queried case field mismatch: {key}"
    except Exception as e:
        pytest.fail(f"Error querying case: {str(e)}")

def test_insert_and_query_metrics(supabase_client: Client, test_case: Dict[str, Any]) -> None:
    """Test decision metrics table operations.
    
    Args:
        supabase_client: Supabase client fixture
        test_case: Test case data fixture
    
    Raises:
        AssertionError: If any test assertions fail
        Exception: If database operations fail
    """
    # Insert prerequisite test case
    try:
        result = supabase_client.table("cases").insert(test_case).execute()
        assert result.data is not None, "Failed to insert prerequisite test case"
        case_id = result.data[0]["external_id"]
    except Exception as e:
        pytest.fail(f"Error inserting prerequisite case: {str(e)}")
    
    # Check table structure
    try:
        result = supabase_client.table("decision_metrics").select("*").limit(1).execute()
        columns = result.data[0].keys() if result.data else []
        required_columns = {"case_id", "decision_type", "decision_value", "confidence", "model", "prompt", "completion"}
        assert all(col in columns for col in required_columns), f"Missing required columns. Found: {columns}"
    except Exception as e:
        pytest.fail(f"Error checking decision_metrics table structure: {str(e)}")
    
    # Create and insert test metric
    test_metric = {
        "case_id": case_id,
        "decision_type": "risk_assessment",
        "decision_value": json.dumps({"risk": "high"}),
        "confidence": 0.85,
        "risk_level": "High",
        "priority": 1,
        "needs_investigation": True,
        "automated_actions": ["notify_team"],
        "required_human_actions": ["review_case"],
        "model": "gpt-4",
        "prompt": "Test prompt",
        "completion": "Test completion"
    }
    
    try:
        result = supabase_client.table("decision_metrics").insert(test_metric).execute()
        assert result.data is not None, "Failed to insert test metric"
        inserted_metric = result.data[0]
        for key, value in test_metric.items():
            if key != "decision_value":  # Skip JSONB comparison
                assert inserted_metric[key] == value, f"Metric field mismatch: {key}"
    except Exception as e:
        pytest.fail(f"Error inserting metric: {str(e)}")
    
    # Query test metric
    try:
        result = supabase_client.table("decision_metrics").select("*").eq("case_id", case_id).execute()
        assert result.data is not None and len(result.data) == 1, "Failed to query metric"
        queried_metric = result.data[0]
        for key, value in test_metric.items():
            if key != "decision_value":  # Skip JSONB comparison
                assert queried_metric[key] == value, f"Queried metric field mismatch: {key}"
    except Exception as e:
        pytest.fail(f"Error querying metric: {str(e)}")
