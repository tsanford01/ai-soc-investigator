import requests
from tenacity import retry, stop_after_attempt, wait_exponential
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from auth import AuthManager
import logging

logger = logging.getLogger(__name__)

class APIClient:
    def __init__(self, auth_manager: AuthManager):
        self.auth_manager = auth_manager
        self.session = requests.Session()
        self.session.verify = False  # For testing only
        
    def _get_headers(self) -> Dict[str, str]:
        """Get headers with current valid token."""
        token = self.auth_manager.get_valid_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1)
    )
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """Make an HTTP request to the API with retry logic."""
        if 'headers' not in kwargs:
            kwargs['headers'] = self._get_headers()
            
        url = f"https://{self.auth_manager.host}/connect/api/v1{endpoint}"
        logger.info(f"Making request to: {url}")
        
        response = self.session.request(method, url, **kwargs)
        
        if response.status_code == 401:
            # Token might be expired, force refresh and retry
            logger.info("Token expired, refreshing...")
            new_token = self.auth_manager._get_access_token()
            if new_token:
                kwargs['headers'] = self._get_headers()
                response = self.session.request(method, url, **kwargs)
            else:
                raise Exception("Failed to refresh token")
            
        response.raise_for_status()
        return response.json()

    def list_cases(
        self,
        status: Optional[List[str]] = None,
        severity: Optional[List[str]] = None,
        min_score: Optional[float] = None,
        limit: int = 50,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> Dict[str, Any]:
        """Get a list of cases matching the specified criteria."""
        params = []
        
        if status:
            params.append(f"status={','.join(status)}")
        if severity:
            params.append(f"severity={','.join(severity)}")
        if min_score is not None:
            params.append(f"min_score={min_score}")
        
        params.extend([
            f"limit={limit}",
            f"sort={sort_by}",
            f"order={sort_order}"
        ])
        
        endpoint = f"/cases?{'&'.join(params)}"
        response = self._make_request("GET", endpoint)
        
        # Handle the nested response structure
        if isinstance(response, dict) and 'data' in response and 'cases' in response['data']:
            return {'items': response['data']['cases']}
        return {'items': []}

    def get_case(self, case_id: str) -> Dict[str, Any]:
        """Get details for a specific case."""
        response = self._make_request("GET", f"/cases/{case_id}")
        if isinstance(response, dict) and 'data' in response:
            return response['data']
        return response

    def get_case_summary(self, case_id: str) -> Dict[str, Any]:
        """Get the summary for a specific case."""
        response = self._make_request("GET", f"/cases/{case_id}/summary")
        if isinstance(response, dict) and 'data' in response:
            return response['data']
        return response

    def get_case_alerts(self, case_id: str, skip: int = 0, limit: int = 50) -> Dict[str, Any]:
        """Get alerts associated with a case."""
        endpoint = f"/cases/{case_id}/alerts?skip={skip}&limit={limit}"
        response = self._make_request("GET", endpoint)
        if isinstance(response, dict) and 'data' in response and 'alerts' in response['data']:
            return {'items': response['data']['alerts']}
        return {'items': []}

    def get_case_activities(self, case_id: str) -> Dict[str, Any]:
        """Get activities for a specific case."""
        response = self._make_request("GET", f"/cases/{case_id}/activities")
        if isinstance(response, dict) and 'data' in response and 'activities' in response['data']:
            return {'items': response['data']['activities']}
        return {'items': []}

    def update_case(
        self,
        case_id: str,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        assignee: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Update a case with new information."""
        data = {}
        if status:
            data["status"] = status
        if severity:
            data["severity"] = severity
        if assignee:
            data["assignee"] = assignee
        if tags:
            data["tags"] = tags

        return self._make_request("PUT", f"/cases/{case_id}", json=data)

    def add_case_comment(self, case_id: str, comment: str) -> Dict[str, Any]:
        """Add a comment to a case."""
        data = {"comment": comment}
        return self._make_request("POST", f"/cases/{case_id}/comments", json=data)
        
    def get_alerts(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        severity: Optional[List[str]] = None,
        limit: int = 50
    ) -> Dict[str, Any]:
        """Get alerts within a specific time range."""
        params = [f"limit={limit}"]
        
        if start_time:
            params.append(f"start_time={start_time.isoformat()}")
        if end_time:
            params.append(f"end_time={end_time.isoformat()}")
        if severity:
            params.append(f"severity={','.join(severity)}")
            
        endpoint = f"/alerts?{'&'.join(params)}"
        return self._make_request("GET", endpoint)
        
    def get_alert(self, alert_id: str) -> Dict[str, Any]:
        """Get details for a specific alert."""
        return self._make_request("GET", f"/alerts/{alert_id}")
        
    def get_recent_alerts(self, hours: int = 24, limit: int = 50) -> Dict[str, Any]:
        """Get alerts from the last N hours."""
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        return self.get_alerts(start_time=start_time, end_time=end_time, limit=limit)

    def get_tenants(self) -> Dict:
        """
        Get list of available tenants
        
        Returns:
            Dict containing tenant information
        """
        response = self._make_request('GET', '/tenants')
        # Log the raw response for debugging
        logger.debug(f"Raw tenant response: {response}")
        return response
