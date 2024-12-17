"""
Unit tests for rate limiter functionality
"""
import pytest
import asyncio
from src.utils.rate_limiter import RateLimiter

@pytest.mark.asyncio
async def test_rate_limiter_basic():
    """Test basic rate limiting functionality"""
    limiter = RateLimiter(calls=2, period=1.0)
    
    # First two calls should succeed
    assert await limiter.acquire()
    assert await limiter.acquire()
    
    # Third call should fail
    assert not await limiter.acquire()
    
    # After waiting, should succeed again
    await asyncio.sleep(1.1)
    assert await limiter.acquire()

@pytest.mark.asyncio
async def test_rate_limiter_concurrent():
    """Test rate limiter under concurrent access"""
    limiter = RateLimiter(calls=3, period=1.0)
    
    async def make_request() -> bool:
        return await limiter.acquire()
    
    # Make 5 concurrent requests
    results = await asyncio.gather(
        *[make_request() for _ in range(5)]
    )
    
    # Only first 3 should succeed
    assert sum(results) == 3
