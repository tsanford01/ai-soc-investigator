import time
import logging
from typing import Optional, NoReturn
from case_selection_agent import CaseSelectionAgent
from investigation_agent import InvestigationAgent
from notification_agent import NotificationAgent
from config import settings
import signal
import sys
from datetime import datetime
import asyncio

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CoordinationAgent:
    def __init__(self):
        self.case_selector = CaseSelectionAgent()
        self.investigator = InvestigationAgent()
        self.notifier = NotificationAgent()
        self.running = True
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

    def _handle_shutdown(self, signum: int, frame) -> None:
        """Handle shutdown signals gracefully."""
        logger.info("Shutdown signal received, stopping gracefully...")
        self.running = False

    async def run_forever(self) -> NoReturn:
        """
        Main loop that coordinates the case investigation process.
        Runs until shutdown signal is received.
        """
        logger.info("Starting Coordination Agent...")
        
        while self.running:
            try:
                await self._process_next_case()
                
                # Sleep between iterations
                logger.info(f"Sleeping for {settings.POLLING_INTERVAL_SECONDS} seconds...")
                for _ in range(settings.POLLING_INTERVAL_SECONDS):
                    if not self.running:
                        break
                    await asyncio.sleep(1)
                    
            except Exception as e:
                logger.error(f"Error in main loop: {str(e)}")
                await asyncio.sleep(settings.RETRY_DELAY_SECONDS)

        logger.info("Coordination Agent stopped.")

    async def _process_next_case(self) -> None:
        """Process the next available case that needs investigation."""
        # Select next case
        case = self.case_selector.select_next_case()
        if not case:
            logger.info("No cases to process at this time")
            return

        try:
            case_id = case.get("_id")
            ticket_id = case.get("ticket_id")
            logger.info(f"Processing case {ticket_id} ({case_id})")

            # Investigate the case
            investigation_results = await self.investigator.investigate_case(case_id)

            # Check if human intervention is needed
            if investigation_results["needs_human"]:
                logger.info(f"Case {ticket_id} requires human attention, sending notification")
                notification_success = self.notifier.notify_case_escalation(investigation_results)
                
                if notification_success:
                    logger.info(f"Successfully escalated case {ticket_id}")
                else:
                    logger.error(f"Failed to send notification for case {ticket_id}")
            else:
                logger.info(f"Case {ticket_id} does not require human intervention")

        except Exception as e:
            logger.error(f"Error processing case {case.get('ticket_id', 'unknown')}: {str(e)}")

if __name__ == "__main__":
    coordinator = CoordinationAgent()
    asyncio.run(coordinator.run_forever())
