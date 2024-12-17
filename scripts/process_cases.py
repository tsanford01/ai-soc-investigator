"""Script for processing security cases and their associated data."""
import asyncio
import logging
from dotenv import load_dotenv
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from uuid import uuid4

from src.clients.api_client import APIClient
from src.clients.supabase_client import SupabaseClient
from src.agents.registry.v2 import AgentRegistry
from src.agents.decision_agent import DecisionAgent
from src.agents.ai_agent import AIAgent
from src.clients.auth import AuthManager
from src.config.settings import load_settings

logger = logging.getLogger(__name__)

class CaseProcessor:
    """Processes security cases and their associated data."""

    def __init__(self, api_client: APIClient, supabase: SupabaseClient):
        """Initialize the case processor."""
        self.api = api_client
        self.supabase = supabase
        self.settings = load_settings()
        self.registry = AgentRegistry()
        self.ai_agent = AIAgent()
        self.decision_agent = DecisionAgent(api_client, supabase, self.registry)
        self.last_processed_time = datetime.now() - timedelta(days=7)  # Default to last 7 days
        self.semaphore = asyncio.Semaphore(3)  # Reduce concurrent operations from 5 to 3

    async def process_cases(self, limit: int = 1) -> None:
        """Process a batch of cases.
        
        Args:
            limit: Maximum number of cases to process in this batch (default: 1)
        """
        try:
            logger.info(f"Fetching cases since {self.last_processed_time}")
            cases = await self.api.list_cases(since=self.last_processed_time, limit=limit)
            logger.info(f"Found {len(cases)} cases")

            if not cases:
                logger.info("No new cases to process")
                return

            # Process just one case
            case = cases[0]
            try:
                await self.process_single_case(case)
                # Update last processed time only if successful
                self.last_processed_time = datetime.fromtimestamp(case.get('created_at', 0) / 1000)
                logger.info(f"Successfully processed case {case.get('_id')}")
            except Exception as e:
                logger.error(f"Error processing case {case.get('_id')}: {e}")
                await self.registry.publish_event(
                    'case_processing_error',
                    {
                        'case_id': case.get('_id'),
                        'error': str(e),
                        'error_id': str(uuid4())
                    }
                )

        except Exception as e:
            logger.error(f"Error in process_cases: {e}")
            raise

    async def process_single_case(self, case: Dict[str, Any]) -> None:
        """Process a single case and its associated data."""
        case_id = case.get('_id')
        logger.info(f"Processing case {case_id}")

        try:
            # Make decisions about the case
            decisions = await self.decision_agent.make_decisions(case_id, case)
            logger.info(f"Decisions for case {case_id}: {decisions}")

            # Update the case status
            try:
                await self.api.update_case_status(case_id, decisions)
                logger.info(f"Successfully updated case {case_id} status")
            except Exception as e:
                logger.error(f"Error updating case {case_id} status: {e}")

            # Process alerts and observables regardless of decision
            await self.process_case_alerts(case)
            await self.process_case_observables(case)

            # Only process activities if needed
            if decisions["needs_investigation"]:
                await self.process_case_activities(case)

        except Exception as e:
            logger.error(f"Error processing case {case_id}: {e}")
            raise

    async def process_case_alerts(self, case: Dict[str, Any]) -> None:
        """Process all alerts for a case with pagination.
        
        Args:
            case: The case data from the list_cases API
        """
        skip = 0
        batch_size = 5  # Reduced from 10 to 5
        total_alerts = 0

        while True:
            alerts = await self.api.get_case_alerts(case['_id'], skip=skip, limit=batch_size)
            if not alerts:
                break

            # Process alerts concurrently with semaphore
            tasks = []
            for alert in alerts:
                tasks.append(self._process_single_alert(case['_id'], alert))
            
            # Wait for all alerts in this batch to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Count successful upserts
            total_alerts += sum(1 for r in results if not isinstance(r, Exception))
            
            # Log any errors
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Error processing alert {i} for case {case['_id']}: {result}")

            skip += batch_size
            logger.info(f"Processed {total_alerts} alerts for case {case['_id']}")
            
            # Increased delay between batches
            await asyncio.sleep(1.0)  # Increased from 0.5 to 1.0 seconds

    async def _process_single_alert(self, case_id: str, alert: Dict[str, Any]) -> None:
        """Process a single alert with concurrency control.
        
        Args:
            case_id: External case ID
            alert: Alert data to process
        """
        async with self.semaphore:
            # Get case UUID from Supabase
            case_data = await self.supabase.client.table("cases").select("id").eq("case_id", case_id).execute()
            if not case_data.data:
                raise ValueError(f"Case {case_id} not found in Supabase")
            case_uuid = case_data.data[0]["id"]
            await self.supabase.upsert_alert_data(case_id, case_uuid, alert)

    async def process_case_observables(self, case: Dict[str, Any]) -> None:
        """Process all observables for a case.
        
        Args:
            case: The case data from the list_cases API
        """
        try:
            logger.info(f"Fetching observables for case {case['_id']}")
            observables = await self.api.get_case_observables(case['_id'])
            logger.info(f"Found {len(observables)} observables for case {case['_id']}")
            
            total_observables = 0
            
            # Process observables in batches of 10
            batch_size = 10
            for i in range(0, len(observables), batch_size):
                batch = observables[i:i + batch_size]
                logger.info(f"Processing batch {i//batch_size + 1} of observables for case {case['_id']}")
                
                # Process batch concurrently
                tasks = []
                for observable in batch:
                    tasks.append(self._process_single_observable(case['_id'], observable))
                
                # Wait for batch to complete
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Count successful upserts and log errors
                batch_success = sum(1 for r in results if not isinstance(r, Exception))
                total_observables += batch_success
                logger.info(f"Successfully processed {batch_success}/{len(batch)} observables in batch {i//batch_size + 1}")
                
                for j, result in enumerate(results):
                    if isinstance(result, Exception):
                        logger.error(f"Error processing observable {i+j} for case {case['_id']}: {result}")
                
                # Small delay between batches
                await asyncio.sleep(0.5)
                
            logger.info(f"Completed processing {total_observables} observables for case {case['_id']}")
            
        except Exception as e:
            logger.error(f"Error processing observables for case {case['_id']}: {e}")
            raise

    async def _process_single_observable(self, case_id: str, observable: Dict[str, Any]) -> None:
        """Process a single observable with concurrency control.
        
        Args:
            case_id: External case ID
            observable: Observable data to process
        """
        async with self.semaphore:
            # Get case UUID from Supabase
            case_data = await self.supabase.client.table("cases").select("id").eq("case_id", case_id).execute()
            if not case_data.data:
                raise ValueError(f"Case {case_id} not found in Supabase")
            case_uuid = case_data.data[0]["id"]
            await self.supabase.upsert_observable_data(case_id, case_uuid, observable)

    async def process_case_activities(self, case: Dict[str, Any]) -> None:
        """Process all activities for a case.
        
        Args:
            case: The case data from the list_cases API
        """
        try:
            logger.info(f"Fetching activities for case {case['_id']}")
            response = await self.api.get_case_activities(case['_id'])
            activities = response.get('data', [])
            logger.info(f"Found {len(activities)} activities for case {case['_id']}")
            
            total_activities = 0
            for activity in activities:
                try:
                    await self._process_single_activity(case['_id'], activity)
                    total_activities += 1
                except Exception as e:
                    logger.error(f"Error processing activity for case {case['_id']}: {e}")
                    continue
            
            logger.info(f"Processed {total_activities} activities for case {case['_id']}")
            
        except Exception as e:
            logger.error(f"Error processing activities for case {case['_id']}: {e}")
            raise

    async def _process_single_activity(self, case_id: str, activity: Dict[str, Any]) -> None:
        """Process a single activity with concurrency control.
        
        Args:
            case_id: External case ID
            activity: Activity data to process
        """
        async with self.semaphore:
            # Get case UUID from Supabase
            case_data = await self.supabase.client.table("cases").select("id").eq("case_id", case_id).execute()
            if not case_data.data:
                raise ValueError(f"Case {case_id} not found in Supabase")
            case_uuid = case_data.data[0]["id"]
            await self.supabase.upsert_activity_data(case_id, case_uuid, activity)

async def main():
    """Main entry point for the script."""
    try:
        # Load environment variables
        load_dotenv()
        
        # Initialize auth and clients
        settings = load_settings()
        auth_manager = AuthManager()
        api_client = APIClient(auth_manager)
        supabase = SupabaseClient()
        
        # Initialize processor
        processor = CaseProcessor(api_client, supabase)
        
        # Register capabilities
        await processor.registry.register_capability(
            "analyze_case",
            processor.ai_agent.analyze_case
        )
        await processor.registry.register_capability(
            "investigate_case",
            processor.ai_agent.analyze_case  # Using same method for now, can be specialized later
        )
        
        # Process cases
        await processor.process_cases(limit=1)
        
    except Exception as e:
        logger.error(f"Main process failed: {e}")
        raise

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
