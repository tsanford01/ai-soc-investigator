"""
Configuration settings management for the Security Case Investigation Agent System.
"""
from typing import Dict, Any, Optional
from pathlib import Path
import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Environment Configuration
    ENVIRONMENT_URL: str = Field(default=..., description="Environment URL")
    
    # Authentication Configuration
    STELLAR_USERNAME: str = Field(default=..., description="Username")
    REFRESH_TOKEN: str = Field(default=..., description="Refresh token")
    ACCESS_TOKEN: Optional[str] = Field(default=None, description="Access token")
    TOKEN_EXPIRY: Optional[str] = Field(default=None, description="Token expiry timestamp")
    
    # Database Configuration
    SUPABASE_URL: str = Field(default=..., description="Supabase URL")
    SUPABASE_KEY: str = Field(default=..., description="Supabase key")
    
    # Slack Configuration
    SLACK_TOKEN: str = Field(default=..., description="Slack API token")
    SLACK_CHANNEL: str = Field(default=..., description="Slack channel for notifications")
    
    # OpenAI Configuration
    OPENAI_API_KEY: str = Field(default=..., description="OpenAI API key")
    
    # Agent Configuration
    MAX_RETRIES: int = Field(default=3, description="Maximum number of retries")
    RETRY_DELAY: float = Field(default=1.0, description="Delay between retries in seconds")
    RATE_LIMIT_CALLS: int = Field(default=100, description="Maximum calls per period")
    RATE_LIMIT_PERIOD: float = Field(default=60.0, description="Rate limit period in seconds")
    
    # Logging Configuration
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        env_file_encoding="utf-8"
    )

def load_settings() -> Settings:
    """Load settings from environment variables and .env file"""
    return Settings()
