"""
Rate limiting utilities for API requests and agent operations.
"""
from datetime import datetime
import asyncio
from typing import List

class RateLimiter:
    """Rate limiter implementation using token bucket algorithm"""
    
    def __init__(self, calls: int, period: float):
        """
        Initialize rate limiter
        
        Args:
            calls: Maximum number of calls allowed in the period
            period: Time period in seconds
        """
        self.calls = calls
        self.period = period
        self.timestamps: List[float] = []
        self._lock = asyncio.Lock()
    
    async def acquire(self) -> bool:
        """
        Acquire a rate limit token
        
        Returns:
            bool: True if token acquired, False if rate limit exceeded
        """
        async with self._lock:
            now = datetime.now().timestamp()
            
            # Remove timestamps older than the period
            cutoff = now - self.period
            self.timestamps = [ts for ts in self.timestamps if ts > cutoff]
            
            # Check if we can make another call
            if len(self.timestamps) >= self.calls:
                return False
                
            self.timestamps.append(now)
            return True
