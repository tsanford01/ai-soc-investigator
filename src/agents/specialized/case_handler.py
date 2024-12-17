"""Case handler agent implementation."""
import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta

from src.agents.base import BaseAgent
from src.agents.registry import AgentRegistry
from src.clients.api_client import APIClient
from src.clients.supabase_client import SupabaseWrapper
from src.utils.retry import RetryConfig

logger = logging.getLogger(__name__)

class CaseHandlerAgent(BaseAgent):
    """Agent for handling security cases."""

    def __init__(
        self,
        registry: AgentRegistry,
        api_client: APIClient,
        supabase: SupabaseWrapper,
        retry_config: RetryConfig,
    ) -> None:
        """Initialize the case handler agent."""
        super().__init__(registry, retry_config)
        self.api_client = api_client
        self.supabase = supabase

    async def _initialize_capabilities(self) -> None:
        """Initialize agent capabilities."""
        await self.registry.register_capability("process_case", self.process_case)
        await self.registry.register_capability("list_recent_cases", self.list_recent_cases)

    async def analyze_case_data(
        self,
        case_id: str,
        details: Dict[str, Any],
        summary: Dict[str, Any],
        alerts: List[Dict[str, Any]],
        activities: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze case data like a SOC analyst would.
        Returns analysis results and recommendations.
        """
        analysis = {
            "case_id": case_id,
            "findings": [],
            "indicators": [],
            "risk_level": "unknown",
            "confidence": "low",
            "needs_action": False,
            "recommended_actions": [],
            "reasoning": []
        }

        # 1. Initial Case Review
        analysis["findings"].append(f"Case Severity: {details.get('severity', 'unknown')}")
        analysis["findings"].append(f"Case Status: {details.get('status', 'unknown')}")
        
        # 2. Alert Analysis
        if alerts:
            alert_types = [alert["type"] for alert in alerts]
            analysis["findings"].append(f"Alert Types Found: {', '.join(alert_types)}")
            
            # Look for critical alert types
            critical_types = ["malware", "ransomware", "data_exfiltration"]
            found_critical = [t for t in alert_types if t in critical_types]
            if found_critical:
                analysis["indicators"].append("Critical Alert Types Detected")
                analysis["risk_level"] = "high"
                analysis["confidence"] = "high"
                analysis["needs_action"] = True
                analysis["reasoning"].append(
                    f"Critical alert types found: {', '.join(found_critical)}"
                )

        # 3. Activity Pattern Analysis
        if activities:
            activity_types = [act["type"] for act in activities]
            analysis["findings"].append(
                f"Activity Types Found: {', '.join(activity_types)}"
            )
            
            # Check for investigation patterns
            investigations = [a for a in activities if a["type"] == "investigation"]
            if investigations:
                analysis["indicators"].append("Prior Investigations Found")
                analysis["reasoning"].append(
                    f"Found {len(investigations)} prior investigations"
                )
                analysis["confidence"] = "medium"

        # 4. Risk Assessment
        if not analysis["risk_level"] or analysis["risk_level"] == "unknown":
            if details.get("severity") == "high":
                analysis["risk_level"] = "high"
                analysis["needs_action"] = True
                analysis["reasoning"].append("High severity case requires attention")
            elif details.get("severity") == "medium" and len(alerts) > 1:
                analysis["risk_level"] = "medium"
                analysis["needs_action"] = True
                analysis["reasoning"].append(
                    "Medium severity with multiple alerts suggests potential threat"
                )
            else:
                analysis["risk_level"] = "low"
                analysis["reasoning"].append("No critical indicators found")

        # 5. Action Recommendations
        if analysis["needs_action"]:
            if analysis["risk_level"] == "high":
                analysis["recommended_actions"].extend([
                    "Immediate investigation required",
                    "Escalate to senior analyst",
                    "Implement containment measures"
                ])
            elif analysis["risk_level"] == "medium":
                analysis["recommended_actions"].extend([
                    "Review alerts in detail",
                    "Check for related cases",
                    "Monitor for escalation"
                ])

        return analysis

    async def process_case(self, case_id: str, correlation_id: str) -> Dict[str, Any]:
        """Process a specific case."""
        try:
            logger.info(f"Starting analysis of case {case_id}")
            
            # 1. Gather all case information
            case_details = await self.api_client.get_case_details(case_id)
            case_summary = await self.api_client.get_case_summary(case_id)
            case_alerts = await self.api_client.get_case_alerts(case_id)
            case_activities = await self.api_client.get_case_activities(case_id)

            # 2. Analyze the case data
            analysis = await self.analyze_case_data(
                case_id,
                case_details,
                case_summary,
                case_alerts,
                case_activities
            )

            # 3. Prepare case data with analysis
            case_data = {
                "case_id": case_id,
                "details": case_details,
                "summary": case_summary,
                "alerts": case_alerts,
                "activities": case_activities,
                "analysis": analysis,
                "processed_at": datetime.utcnow().isoformat(),
                "correlation_id": correlation_id
            }

            # 4. Store results
            await self.supabase.upsert("cases", case_data)

            # 5. Publish appropriate event based on analysis
            event_type = (
                "case_threat_detected" if analysis["needs_action"]
                else "case_no_threat_detected"
            )
            
            await self.registry.publish_event(
                event_type,
                {
                    "case_id": case_id,
                    "correlation_id": correlation_id,
                    "risk_level": analysis["risk_level"],
                    "confidence": analysis["confidence"],
                    "findings": analysis["findings"],
                    "reasoning": analysis["reasoning"],
                    "recommended_actions": analysis["recommended_actions"],
                    "needs_action": analysis["needs_action"]
                }
            )

            logger.info(
                f"Completed analysis of case {case_id}. "
                f"Risk Level: {analysis['risk_level']}, "
                f"Needs Action: {analysis['needs_action']}"
            )

            return case_data

        except Exception as e:
            logger.error(f"Error processing case {case_id}: {e}")
            await self.registry.publish_event(
                "case_processing_error",
                {
                    "case_id": case_id,
                    "correlation_id": correlation_id,
                    "error": str(e)
                }
            )
            raise

    async def list_recent_cases(
        self,
        hours: int = 24,
        limit: int = 50,
        correlation_id: str = None
    ) -> List[Dict[str, Any]]:
        """List recent cases."""
        try:
            since = datetime.utcnow() - timedelta(hours=hours)
            cases = await self.api_client.list_cases(since=since, limit=limit)

            # Publish success event
            if correlation_id:
                await self.registry.publish_event(
                    "case_listing_complete",
                    {
                        "correlation_id": correlation_id,
                        "result": cases,
                        "hours": hours,
                        "limit": limit
                    }
                )

            return cases

        except Exception as e:
            logger.error(f"Error listing recent cases: {e}")
            if correlation_id:
                await self.registry.publish_event(
                    "case_processing_error",
                    {
                        "correlation_id": correlation_id,
                        "error": str(e)
                    }
                )
            raise
