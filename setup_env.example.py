"""
Environment setup template for the Security Case Investigation Agent System.
Copy this file to setup_env.py and fill in your API keys and configuration.
"""

import os
from dotenv import load_dotenv

def setup_environment():
    """
    Set up environment variables for the application.
    Copy this file to setup_env.py and replace placeholder values with your actual credentials.
    """
    # Load existing environment variables
    load_dotenv()
    
    # Set required environment variables
    env_vars = {
        # Required API Keys
        'OPENAI_API_KEY': 'your-openai-api-key-here',
        'SUPABASE_URL': 'your-supabase-url',
        'SUPABASE_KEY': 'your-supabase-key',
        
        # Optional Notification Settings
        'SLACK_BOT_TOKEN': 'your-slack-bot-token-here',
        'SLACK_CHANNEL_ID': 'your-slack-channel-id',
        
        # Performance and Reliability Settings
        'EXECUTION_TIME_THRESHOLD': '300',  # Maximum execution time in seconds
        'SUCCESS_RATE_THRESHOLD': '0.95',   # Required success rate (0.0-1.0)
        'MAX_RETRIES': '3',                 # Maximum retry attempts
        'RETRY_DELAY': '5',                 # Delay between retries in seconds
        
        # Logging and Monitoring
        'LOG_LEVEL': 'INFO',                # Logging level (DEBUG, INFO, WARNING, ERROR)
        'ENABLE_PERFORMANCE_METRICS': 'true' # Enable performance tracking
    }
    
    # Set environment variables if not already set
    for key, value in env_vars.items():
        if not os.getenv(key):
            os.environ[key] = value

if __name__ == '__main__':
    setup_environment()
