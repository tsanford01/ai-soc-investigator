"""
Data processor agent for handling data processing tasks.
"""
from typing import Dict, Any, Optional
import logging
import random
import asyncio

from ..base import BaseAgent
from ..registry import AgentRegistry
from ...utils.retry import RetryConfig

logger = logging.getLogger(__name__)

class DataProcessorAgent(BaseAgent):
    """
    Agent for processing and transforming data.
    
    Features:
    - Data transformation
    - Error simulation for testing
    - Configurable processing time
    """
    
    def __init__(
        self, 
        registry: AgentRegistry, 
        error_rate: float = 0.2,
        processing_time: float = 0.5,
        retry_config: Optional[RetryConfig] = None
    ):
        """
        Initialize data processor agent.
        
        Args:
            registry: Agent registry
            error_rate: Probability of simulated errors
            processing_time: Simulated processing time in seconds
            retry_config: Configuration for retry behavior
        """
        self.error_rate = error_rate
        self.processing_time = processing_time
        super().__init__(
            registry, 
            retry_config=retry_config or RetryConfig(max_retries=3)
        )
    
    async def _initialize_capabilities(self) -> None:
        """Initialize data processing capabilities."""
        self.add_capability(
            "process_data",
            "Process and transform data",
            {
                "data": "Data to process",
                "transform_type": "Type of transformation to apply",
                "correlation_id": "Correlation ID for the request"
            },
            "Processed data result"
        )
    
    async def _process_capability_request(self, request_data: Dict[str, Any]) -> Any:
        """
        Process a data processing request.
        
        Args:
            request_data: Request data including parameters
            
        Returns:
            Processed data result
            
        Raises:
            Exception: If processing fails (simulated)
        """
        # Simulate processing time
        await asyncio.sleep(self.processing_time)
        
        # Simulate random failures
        if random.random() < self.error_rate:
            raise Exception("Random processing error")
        
        data = request_data.get("params", {}).get("data")
        if not data:
            raise ValueError("No data provided for processing")
            
        transform_type = request_data.get("params", {}).get("transform_type", "default")
        correlation_id = request_data.get("params", {}).get("correlation_id")
        
        # Process the data based on transform type
        result = await self._apply_transformation(data, transform_type)
        
        # Publish processing completion event
        await self.registry.publish("processing_complete", {
            "processor_id": self.agent_id,
            "original_data": data,
            "processed_data": result,
            "transform_type": transform_type,
            "retry_count": request_data.get("retry_count", 0),
            "correlation_id": correlation_id
        })
        
        return result
    
    async def _apply_transformation(self, data: Any, transform_type: str) -> Any:
        """
        Apply the specified transformation to the data.
        
        Args:
            data: Data to transform
            transform_type: Type of transformation to apply
            
        Returns:
            Transformed data
        """
        if transform_type == "uppercase" and isinstance(data, str):
            return data.upper()
        elif transform_type == "lowercase" and isinstance(data, str):
            return data.lower()
        elif transform_type == "reverse" and isinstance(data, str):
            return data[::-1]
        else:
            return data  # Default transformation (identity)
