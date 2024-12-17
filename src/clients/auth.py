"""Authentication manager for API clients."""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import aiohttp
import base64
from urllib.parse import urlparse

from src.config.settings import load_settings

logger = logging.getLogger(__name__)

class AuthManager:
    """Manages authentication tokens and session state."""

    def __init__(self) -> None:
        """Initialize the auth manager."""
        self.settings = load_settings()
        self.access_token = None
        self.refresh_token = self.settings.REFRESH_TOKEN
        self.token_expiry = None

    async def get_access_token(self) -> str:
        """Get a valid access token, refreshing if necessary."""
        if not self.access_token or self.is_token_expired():
            await self.refresh_tokens()
        return self.access_token

    def is_token_expired(self) -> bool:
        """Check if the current access token is expired."""
        if not self.token_expiry:
            return True
        return datetime.utcnow() >= self.token_expiry

    async def refresh_tokens(self) -> None:
        """Refresh the access and refresh tokens."""
        # Get hostname from environment URL
        hostname = urlparse(self.settings.ENVIRONMENT_URL).netloc
        
        # Create Basic Auth header
        auth = base64.b64encode(
            f"{self.settings.STELLAR_USERNAME}:{self.refresh_token}".encode()
        ).decode()
        
        async with aiohttp.ClientSession() as session:
            url = f"https://{hostname}/connect/api/v1/access_token"
            headers = {
                "Authorization": f"Basic {auth}",
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json"
            }
            async with session.post(url, headers=headers) as response:
                response.raise_for_status()
                data = await response.json()
                
                # Update tokens
                self.access_token = data['access_token']
                # Set expiry to 1 hour from now
                self.token_expiry = datetime.utcnow() + timedelta(hours=1)

    async def get_auth_headers(self) -> Dict[str, str]:
        """Get headers for authenticated requests."""
        token = await self.get_access_token()
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }
