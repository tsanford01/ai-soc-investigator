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
        'OPENAI_API_KEY': 'your-openai-api-key-here',
        'SLACK_BOT_TOKEN': 'your-slack-bot-token-here',
        'SLACK_CHANNEL_ID': 'your-slack-channel-id',
        'SUPABASE_URL': 'your-supabase-url',
        'SUPABASE_KEY': 'your-supabase-key',
    }
    
    # Set environment variables if not already set
    for key, value in env_vars.items():
        if not os.getenv(key):
            os.environ[key] = value

if __name__ == '__main__':
    setup_environment()
