from typing import Dict, Any, List
from api_client import APIClient
from openai_agent import OpenAIAgent
from config import settings
import logging
from datetime import datetime
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class InvestigationAgent:
    def __init__(self):
        self.api_client = APIClient()
        self.ai_agent = OpenAIAgent()

    async def investigate_case(self, case_id: str) -> Dict[str, Any]:
        """
        Investigate a case by gathering and analyzing all relevant information.
        Returns a dictionary containing investigation results and recommendations.
        """
        try:
            # Gather all case information
            case_data = self.api_client.get_case(case_id)
            case_summary = self.api_client.get_case_summary(case_id)
            case_alerts = self.api_client.get_case_alerts(case_id)
            case_activities = self.api_client.get_case_activities(case_id)

            # Prepare data for AI analysis
            analysis_data = self._prepare_analysis_data(
                case_data,
                case_summary,
                case_alerts,
                case_activities
            )

            # Get AI analysis
            ai_analysis = await self.ai_agent.analyze_case(analysis_data)

            # Combine all results
            investigation_results = {
                "case_id": case_data.get("data", {}).get("_id"),
                "ticket_id": case_data.get("data", {}).get("ticket_id"),
                "severity": case_data.get("data", {}).get("severity"),
                "score": case_data.get("data", {}).get("score"),
                "alert_count": len(case_alerts.get("data", {}).get("docs", [])),
                "kill_chain_stages": self._extract_kill_chain_stages(case_summary),
                "risk_level": ai_analysis["risk_level"],
                "needs_human": ai_analysis["needs_human"],
                "risk_factors": ai_analysis["risk_factors"],
                "recommendations": ai_analysis["recommendations"],
                "analysis_summary": ai_analysis["analysis_summary"],
                "investigation_time": datetime.utcnow().isoformat()
            }

            logger.info(f"Completed investigation for case {case_id}")
            return investigation_results

        except Exception as e:
            logger.error(f"Error investigating case {case_id}: {str(e)}")
            raise

    def _prepare_analysis_data(
        self,
        case_data: Dict[str, Any],
        case_summary: Dict[str, Any],
        case_alerts: Dict[str, Any],
        case_activities: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Prepare case data for AI analysis.
        """
        return {
            "severity": case_data.get("data", {}).get("severity"),
            "score": case_data.get("data", {}).get("score"),
            "alerts": case_alerts.get("data", {}).get("docs", []),
            "kill_chain_stages": self._extract_kill_chain_stages(case_summary),
            "summary": case_summary.get("data"),
            "activities": case_activities.get("data", [])
        }

    def _extract_kill_chain_stages(self, case_summary: Dict[str, Any]) -> List[str]:
        """Extract unique kill chain stages from case summary."""
        summary_data = case_summary.get("data", {})
        if isinstance(summary_data, dict):
            return summary_data.get("kill_chain_stages", [])
        return []
