"""
Retry utilities for handling transient failures.
"""
from typing import Optional
from dataclasses import dataclass

@dataclass
class RetryConfig:
    """Configuration for retry behavior"""
    
    max_retries: int = 3
    initial_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0
    
    def get_delay(self, retry_count: int) -> float:
        """
        Calculate delay for the current retry attempt
        
        Args:
            retry_count: Current retry attempt number
            
        Returns:
            float: Delay in seconds before next retry
        """
        return min(
            self.initial_delay * 
            (self.exponential_base ** (retry_count - 1)),
            self.max_delay
        )
