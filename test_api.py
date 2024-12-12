import os
from datetime import datetime, timedelta
from auth import AuthManager
from api_client import APIClient
import logging
from dotenv import load_dotenv
from urllib.parse import urlparse

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    # Load environment variables
    load_dotenv()
    
    # Get environment variables
    environment_url = os.getenv('ENVIRONMENT_URL')
    username = os.getenv('STELLAR_USERNAME', '').strip()
    refresh_token = os.getenv('REFRESH_TOKEN')
    
    if not all([environment_url, username, refresh_token]):
        logger.error("Missing required environment variables")
        return
        
    # Clean the URL to get just the host
    parsed_url = urlparse(environment_url)
    host = parsed_url.netloc or environment_url.replace("https://", "")
    
    # Initialize auth manager and authenticate
    auth_manager = AuthManager()
    logger.info("Authenticating...")
    
    access_token = auth_manager.authenticate(host, username, refresh_token)
    if not access_token:
        logger.error("Authentication failed")
        return
        
    logger.info("Successfully authenticated!")
    
    # Initialize API client
    api_client = APIClient(auth_manager)
    
    try:
        # Get tenants first
        logger.info("Fetching tenants...")
        tenants = api_client.get_tenants()
        
        # Log raw response for debugging
        logger.info(f"Tenant response: {tenants}")
        
        if isinstance(tenants, dict):
            if 'items' in tenants:
                logger.info(f"Found {len(tenants['items'])} tenants")
                for tenant in tenants['items']:
                    logger.info(f"Tenant: {tenant.get('name')} (ID: {tenant.get('id')})")
            else:
                # Handle case where response is a dict but doesn't have 'items'
                logger.info("Processing tenant data...")
                if isinstance(tenants, list):
                    logger.info(f"Found {len(tenants)} tenants")
                    for tenant in tenants:
                        logger.info(f"Tenant: {tenant.get('name')} (ID: {tenant.get('id')})")
                else:
                    logger.info(f"Single tenant: {tenants.get('name')} (ID: {tenants.get('id')})")
        else:
            logger.error("Invalid tenant response format")
            logger.error(f"Response type: {type(tenants)}")
            return
        
        # Get recent cases
        logger.info("\nFetching recent cases...")
        cases = api_client.list_cases(limit=5, sort_by="created_at", sort_order="desc")
        
        if not cases or 'items' not in cases:
            logger.error("No cases found or invalid response")
            return
            
        logger.info(f"Found {len(cases.get('items', []))} recent cases")
        
        # Get details for the first case
        if cases.get('items'):
            case = cases['items'][0]
            case_id = case['id']
            logger.info(f"\nGetting details for case {case_id}...")
            
            # Get case details
            case_details = api_client.get_case(case_id)
            logger.info(f"Case Title: {case_details.get('title')}")
            logger.info(f"Status: {case_details.get('status')}")
            logger.info(f"Severity: {case_details.get('severity')}")
            
            # Get case alerts
            alerts = api_client.get_case_alerts(case_id, limit=5)
            logger.info(f"\nFound {len(alerts.get('items', []))} alerts for this case")
            
            # Get case activities
            activities = api_client.get_case_activities(case_id)
            logger.info(f"Found {len(activities.get('items', []))} activities for this case")
        
        # Get recent alerts (last 24 hours)
        logger.info("\nFetching recent alerts...")
        recent_alerts = api_client.get_recent_alerts(hours=24, limit=5)
        
        if not recent_alerts or 'items' not in recent_alerts:
            logger.error("No recent alerts found or invalid response")
            return
            
        logger.info(f"Found {len(recent_alerts.get('items', []))} alerts in the last 24 hours")
        
        if recent_alerts.get('items'):
            alert = recent_alerts['items'][0]
            alert_id = alert['id']
            logger.info(f"\nGetting details for alert {alert_id}...")
            
            # Get alert details
            alert_details = api_client.get_alert(alert_id)
            logger.info(f"Alert Title: {alert_details.get('title')}")
            logger.info(f"Severity: {alert_details.get('severity')}")
            logger.info(f"Created At: {alert_details.get('created_at')}")
            
    except Exception as e:
        logger.error(f"Error occurred: {str(e)}")
        return

if __name__ == "__main__":
    main()
