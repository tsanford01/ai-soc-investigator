"""
Pytest configuration and fixtures
"""
import pytest
import asyncio
from typing import Generator, AsyncGenerator
from src.config.settings import get_test_settings, Settings

@pytest.fixture
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for each test case"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def settings() -> Settings:
    """Provide test settings"""
    return get_test_settings()

@pytest.fixture
async def mock_agent_registry() -> AsyncGenerator:
    """Provide a mock agent registry"""
    # Add mock registry implementation
    yield
