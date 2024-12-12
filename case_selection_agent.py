from typing import Optional, Dict, Any
from api_client import APIClient
from config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CaseSelectionAgent:
    def __init__(self):
        self.api_client = APIClient()
        
    def select_next_case(self) -> Optional[Dict[str, Any]]:
        """
        Select the highest priority case that needs investigation.
        Returns the case data or None if no suitable cases are found.
        """
        try:
            # Get cases matching our criteria
            response = self.api_client.list_cases(
                status=settings.NEW_CASE_STATUSES,
                severity=settings.CRITICAL_SEVERITIES,
                min_score=settings.MIN_CASE_SCORE,
                limit=settings.MAX_CASES_PER_BATCH
            )
            
            cases = response.get("data", {}).get("cases", [])
            if not cases:
                logger.info("No cases found matching selection criteria")
                return None
            
            # Sort cases by priority (score and severity)
            def case_priority(case):
                severity_weights = {
                    "Critical": 4,
                    "High": 3,
                    "Medium": 2,
                    "Low": 1
                }
                return (
                    severity_weights.get(case.get("severity", "Low"), 0),
                    case.get("score", 0)
                )
            
            sorted_cases = sorted(cases, key=case_priority, reverse=True)
            selected_case = sorted_cases[0]
            
            logger.info(
                f"Selected case {selected_case.get('ticket_id')} "
                f"(Severity: {selected_case.get('severity')}, "
                f"Score: {selected_case.get('score')})"
            )
            
            return selected_case
            
        except Exception as e:
            logger.error(f"Error selecting next case: {str(e)}")
            return None
