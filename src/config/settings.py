"""
Configuration settings management for the Security Case Investigation Agent System.
"""
from typing import Dict, Any, Optional
from pathlib import Path
import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # API Configuration
    API_BASE_URL: str = Field(default="http://localhost:8000", description="Base API URL")
    API_KEY: str = Field(default=..., description="API key for authentication")
    
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
    EXECUTION_TIME_THRESHOLD: int = Field(default=300, description="Maximum execution time in seconds")
    SUCCESS_RATE_THRESHOLD: float = Field(default=0.95, description="Required success rate")
    
    # Logging Configuration
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    ENABLE_PERFORMANCE_METRICS: bool = Field(default=True, description="Enable performance tracking")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        env_file_encoding="utf-8",
        extra="allow"
    )
    
    @classmethod
    def get_test_settings(cls) -> "Settings":
        """Create test settings with safe default values"""
        return cls(
            API_BASE_URL="http://test.local",
            API_KEY="test-key",
            SUPABASE_URL="http://supabase.test",
            SUPABASE_KEY="test-key",
            SLACK_TOKEN="test-token",
            SLACK_CHANNEL="test-channel",
            OPENAI_API_KEY="test-key",
            LOG_LEVEL="DEBUG",
            ENABLE_PERFORMANCE_METRICS=True
        )

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()

def get_test_settings() -> Settings:
    """Get test settings instance"""
    return Settings.get_test_settings()
