import asyncio
import logging
from typing import Dict, Any, List
from agent_registry import AgentRegistry
from base_agent import BaseAgent

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataProcessorAgent(BaseAgent):
    def _initialize_capabilities(self) -> None:
        self.add_capability(
            "process_data",
            "Process and transform data",
            ["data"]
        )

    async def _handle_capability_request(self, request_data: Dict[str, Any]) -> None:
        logger.info(f"Handling capability request: {request_data}")  # Debug log
        if request_data.get("capability") == "process_data":
            data = request_data.get("params", {}).get("data")
            if data:
                # Simple processing - convert to uppercase if string
                result = data.upper() if isinstance(data, str) else data
                logger.info(f"Publishing result: {result}")  # Debug log
                
                # Publish the result
                result_data = {
                    "processor_id": self.agent_id,
                    "original_data": data,
                    "processed_data": result
                }
                await self.registry.publish("processing_complete", result_data)
                logger.info(f"Published result data: {result_data}")
                logger.info(f"Processed data: {result}")

class DataRequesterAgent(BaseAgent):
    def __init__(self, registry: AgentRegistry):
        super().__init__(registry)
        # Subscribe to processing results
        self.registry.subscribe("processing_complete", self.handle_processing_result)
        self.received_results = []

    def _initialize_capabilities(self) -> None:
        # This agent doesn't provide any capabilities
        pass

    async def _handle_capability_request(self, request_data: Dict[str, Any]) -> None:
        # This agent doesn't handle any capabilities
        pass

    async def handle_processing_result(self, event_data: Dict[str, Any]) -> None:
        logger.info(f"Raw event data: {event_data}")  # Add debug logging
        self.received_results.append(event_data.get("data", {}))
        logger.info(f"Received processing result: {event_data}")

    async def request_processing(self, data: str) -> None:
        await self.request_capability("process_data", {"data": data})

async def main():
    # Create the registry
    registry = AgentRegistry()
    
    # Create our agents
    processor = DataProcessorAgent(registry)
    requester = DataRequesterAgent(registry)

    # Test the system
    test_data = "hello world"
    logger.info(f"Sending test data: {test_data}")
    
    # Request processing
    await requester.request_processing(test_data)
    
    # Wait a bit to ensure processing completes
    await asyncio.sleep(2)  # Increased wait time
    
    # Verify results
    if requester.received_results:
        result = requester.received_results[0]
        logger.info(f"Final results: {result}")  # Add debug logging
        processed_data = result.get("processed_data")
        assert processed_data == "HELLO WORLD", f"Expected 'HELLO WORLD' but got {processed_data}"
        logger.info("Test passed successfully!")
    else:
        logger.error("No results received!")

if __name__ == "__main__":
    asyncio.run(main())
