"""
Pytest configuration and fixtures
"""
import pytest
import asyncio
from typing import Generator, AsyncGenerator
from src.config.settings import Settings

@pytest.fixture
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for each test case"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def settings() -> Settings:
    """Provide test settings"""
    return Settings(
        API_BASE_URL="http://test.local",
        API_KEY="test-key",
        SUPABASE_URL="http://supabase.test",
        SUPABASE_KEY="test-key",
        SLACK_TOKEN="test-token",
        SLACK_CHANNEL="test-channel",
        OPENAI_API_KEY="test-key",
    )

@pytest.fixture
async def mock_agent_registry() -> AsyncGenerator:
    """Provide a mock agent registry"""
    # Add mock registry implementation
    yield
