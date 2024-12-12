import requests
import base64
import jwt
import time
import logging
from datetime import datetime, timedelta
import urllib3
import os
from dotenv import load_dotenv, set_key

# Disable SSL warnings for testing
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AuthManager:
    def __init__(self):
        self.access_token = None
        self.host = None
        self.userid = None
        self.refresh_token = None
        self.token_expiry = None
        self._load_stored_token()
        
    def _load_stored_token(self):
        """Load stored token and expiry from .env file"""
        load_dotenv()
        self.access_token = os.getenv('ACCESS_TOKEN')
        expiry_str = os.getenv('TOKEN_EXPIRY')
        if expiry_str:
            try:
                self.token_expiry = datetime.fromisoformat(expiry_str)
            except ValueError:
                self.token_expiry = None
        
    def _save_token_to_env(self, token: str, expiry: datetime):
        """Save token and expiry to .env file"""
        env_path = os.path.join(os.path.dirname(__file__), '.env')
        set_key(env_path, 'ACCESS_TOKEN', token)
        set_key(env_path, 'TOKEN_EXPIRY', expiry.isoformat())
        
    def authenticate(self, host: str, userid: str, refresh_token: str) -> str:
        """
        Authenticate with the API and get an access token
        """
        self.host = host.replace("https://", "")
        self.userid = userid
        self.refresh_token = refresh_token
        
        # Check if we have a valid stored token
        if self.access_token and not self._check_token_expiry():
            logger.info("Using stored valid token")
            return self.access_token
            
        return self._get_access_token()
    
    def _get_access_token(self) -> str:
        """
        Get a new access token using Basic Auth with userid and refresh token
        """
        try:
            auth_string = f"{self.userid}:{self.refresh_token}"
            auth_bytes = auth_string.encode('ascii')
            base64_auth = base64.b64encode(auth_bytes).decode('ascii')
            
            headers = {
                'Authorization': f'Basic {base64_auth}',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            url = f"https://{self.host}/connect/api/v1/access_token"
            logger.info(f"Getting access token from: {url}")
            logger.info(f"Using email: {self.userid}")
            
            response = requests.post(url, headers=headers, verify=False)
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get('access_token')
                
                # Decode token to get expiry
                token_data = jwt.decode(self.access_token, options={"verify_signature": False})
                self.token_expiry = datetime.fromtimestamp(token_data['exp'])
                
                # Save token and expiry to .env
                self._save_token_to_env(self.access_token, self.token_expiry)
                
                logger.info("Successfully obtained new access token")
                logger.info(f"Token will expire at: {self.token_expiry}")
                return self.access_token
            else:
                logger.error(f"Failed to get access token. Status: {response.status_code}, Response: {response.text}")
                logger.error(f"Request URL: {url}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting access token: {str(e)}")
            return None
            
    def _check_token_expiry(self) -> bool:
        """
        Check if the token is expired or will expire soon (within 5 minutes)
        """
        if not self.token_expiry:
            return True
            
        # Refresh if token expires in less than 5 minutes
        return datetime.now() + timedelta(minutes=5) >= self.token_expiry
        
    def get_valid_token(self) -> str:
        """
        Get a valid access token, refreshing if necessary
        """
        if not self.access_token or self._check_token_expiry():
            return self._get_access_token()
        return self.access_token
        
    def get_cases(self, limit: int = 10) -> list:
        """
        Get cases using the access token
        """
        token = self.get_valid_token()
        if not token:
            logger.error("No valid token available")
            return None
            
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        url = f"https://{self.host}/connect/api/v1/cases?limit={limit}"
        
        try:
            response = requests.get(url, headers=headers, verify=False)
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get cases. Status: {response.status_code}, Response: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting cases: {str(e)}")
            return None

def authenticate() -> 'APIClient':
    """Authenticate and return an initialized APIClient."""
    from api_client import APIClient  # Import here to avoid circular import
    
    # Load environment variables
    load_dotenv()
    
    # Get environment variables
    environment_url = os.getenv('ENVIRONMENT_URL')
    username = os.getenv('STELLAR_USERNAME', '').strip()
    refresh_token = os.getenv('REFRESH_TOKEN')
    
    if not all([environment_url, username, refresh_token]):
        raise ValueError("Missing required environment variables")
    
    # Initialize auth manager and authenticate
    auth_manager = AuthManager()
    access_token = auth_manager.authenticate(environment_url, username, refresh_token)
    if not access_token:
        raise ValueError("Authentication failed")
    
    # Initialize and return API client
    return APIClient(auth_manager)
