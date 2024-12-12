from pydantic import BaseSettings
from typing import List

class Settings(BaseSettings):
    # API Configuration
    API_BASE_URL: str = "http://localhost:3000/connect/api/v1"
    API_TOKEN: str = ""
    
    # Environment Configuration
    ENVIRONMENT_URL: str = ""
    USERNAME: str = ""
    AUTH_TOKEN: str = ""
    
    # OpenAI Configuration
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4-1106-preview"  # or "gpt-3.5-turbo" for faster, cheaper analysis
    
    # Case Selection Criteria
    MIN_CASE_SCORE: float = 70.0
    CRITICAL_SEVERITIES: List[str] = ["Critical", "High"]
    NEW_CASE_STATUSES: List[str] = ["New"]
    MAX_CASES_PER_BATCH: int = 10
    
    # Investigation Thresholds
    MIN_ALERTS_FOR_ESCALATION: int = 3
    CRITICAL_KILL_CHAIN_STAGES: List[str] = [
        "Command and Control",
        "Actions on Objectives",
        "Exploitation"
    ]
    
    # Slack Configuration
    SLACK_TOKEN: str = ""
    SLACK_CHANNEL: str = "#security-alerts"
    
    # Operational Settings
    POLLING_INTERVAL_SECONDS: int = 300  # 5 minutes
    MAX_RETRIES: int = 3
    RETRY_DELAY_SECONDS: int = 5
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
