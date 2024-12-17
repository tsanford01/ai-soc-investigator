"""API client for interacting with the security platform."""
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
import aiohttp
from urllib.parse import urlparse

from src.clients.auth import AuthManager
from src.utils.retry import RetryConfig
from src.config.settings import load_settings

logger = logging.getLogger(__name__)

class APIClient:
    """Client for interacting with the security platform API."""

    def __init__(self, auth_manager: AuthManager) -> None:
        """Initialize the API client."""
        self.auth_manager = auth_manager
        self.settings = load_settings()
        self.hostname = urlparse(self.settings.ENVIRONMENT_URL).netloc
        self.retry_config = RetryConfig(max_retries=3, initial_delay=1.0)

    async def _make_request(self, method: str, path: str, **kwargs) -> Any:
        """Make an authenticated request to the API."""
        headers = await self.auth_manager.get_auth_headers()
        if 'headers' in kwargs:
            headers.update(kwargs['headers'])
        kwargs['headers'] = headers

        url = f"https://{self.hostname}/connect/api/v1{path}"
        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, **kwargs) as response:
                response.raise_for_status()
                data = await response.json()
                logger.info(f"API response from {path}: {data}")
                return data

    async def get_case_details(self, case_id: str) -> Dict[str, Any]:
        """Get details for a specific case."""
        return await self._make_request('GET', f'/cases/{case_id}')

    async def get_case_summary(self, case_id: str) -> Dict[str, Any]:
        """Get summary for a specific case."""
        return await self._make_request('GET', f'/cases/{case_id}/summary')

    async def get_case_alerts(self, case_id: str, skip: int = 0, limit: int = 50) -> List[Dict[str, Any]]:
        """Get alerts associated with a case.
        
        Args:
            case_id (str): The ID of the case
            skip (int): Number of records to skip before returning results
            limit (int): Maximum number of results to return (max 50)
        
        Returns:
            List[Dict[str, Any]]: List of alerts associated with the case
        """
        params = {
            'skip': skip,
            'limit': min(limit, 50)  # Ensure we don't exceed max limit of 50
        }
        response = await self._make_request('GET', f'/cases/{case_id}/alerts', params=params)
        if isinstance(response, dict) and 'data' in response:
            # The API returns an ESCaseAlerts object with docs array
            docs = response['data'].get('docs', [])
            # Extract the _source field from each doc which contains the actual alert data
            return [doc.get('_source', {}) for doc in docs if doc.get('found', True)]
        return []

    async def get_case_observables(self, case_id: str) -> List[Dict[str, Any]]:
        """Get observables associated with a case.
        
        Args:
            case_id (str): The ID of the case
        
        Returns:
            List[Dict[str, Any]]: List of observables associated with the case
        """
        response = await self._make_request('GET', f'/cases/{case_id}/observables')
        return response.get('data', [])

    async def get_case_activities(self, case_id: str) -> List[Dict[str, Any]]:
        """Get activities associated with a case."""
        return await self._make_request('GET', f'/cases/{case_id}/activities')

    async def list_cases(
        self,
        since: Optional[datetime] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """List cases, optionally filtered by time."""
        params = {'limit': limit}
        if since:
            params['since'] = since.isoformat()
        response = await self._make_request('GET', '/cases', params=params)
        return response['data']['cases']

    async def update_case_status(self, case_id: str, updates: Dict[str, Any]) -> None:
        """Update case status.
        
        Args:
            case_id: The case ID
            updates: The updates to apply
        """
        try:
            # Convert the updates into the API's expected format
            api_updates = {
                "status": "In Progress" if updates.get("needs_investigation") else "Closed",
                "priority": updates.get("priority", 0),
                "automated_actions": updates.get("automated_actions", []),
                "required_human_actions": updates.get("required_human_actions", [])
            }
            
            # Send the update request
            url = f"https://{self.hostname}/connect/api/v1/cases/{case_id}/update"
            async with aiohttp.ClientSession() as session:
                async with session.put(url, json=api_updates, headers=await self.auth_manager.get_auth_headers()) as response:
                    if response.status != 200:
                        raise Exception(f"{response.status}, message='{response.reason}', url='{url}'")
                    
                    logger.info(f"Successfully updated case {case_id} status")
                    
        except Exception as e:
            logger.error(f"Error updating case {case_id} status: {e}")
            raise
