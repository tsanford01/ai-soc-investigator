import os
from auth import AuthManager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_environment():
    """
    Interactive setup script to configure the environment.
    """
    print("\n=== Environment Setup ===\n")
    
    # Get environment information
    environment_url = input("Enter your environment URL (e.g., https://your-environment.com): ").strip()
    username = input("Enter your username: ").strip()
    token = input("Enter your token: ").strip()
    
    # Authenticate and get bearer token
    auth_manager = AuthManager()
    bearer_token = auth_manager.authenticate(environment_url, username, token)
    
    if not bearer_token:
        print("\nError: Failed to authenticate. Please check your credentials and try again.")
        return False
        
    # Update .env file
    env_content = f"""# Environment Configuration
ENVIRONMENT_URL={environment_url}
USERNAME={username}
AUTH_TOKEN={token}

# OpenAI Configuration
OPENAI_API_KEY={os.getenv('OPENAI_API_KEY', '')}

# API Configuration
API_TOKEN={bearer_token}

# Slack Configuration
SLACK_TOKEN={os.getenv('SLACK_TOKEN', '')}
SLACK_CHANNEL={os.getenv('SLACK_CHANNEL', '#security-alerts')}
"""
    
    try:
        with open('.env', 'w') as f:
            f.write(env_content)
        print("\nConfiguration saved successfully!")
        print("Bearer token has been generated and saved to .env file")
        return True
        
    except Exception as e:
        print(f"\nError saving configuration: {str(e)}")
        return False

if __name__ == "__main__":
    setup_environment()
