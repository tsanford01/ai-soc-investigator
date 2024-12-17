"""Decision making agent for case processing workflow."""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid
import json

from src.clients.api_client import APIClient
from src.clients.supabase_client import SupabaseClient
from src.agents.registry.v2 import AgentRegistry
from src.agents.ai_agent import AIAgent  # Import AIAgent

logger = logging.getLogger(__name__)

class DecisionAgent:
    """Agent responsible for making decisions about case processing workflow."""

    def __init__(self, api_client: APIClient, supabase: SupabaseClient, registry: AgentRegistry):
        """Initialize the decision agent."""
        self.api = api_client
        self.supabase = supabase
        self.registry = registry
        self.ai_agent = AIAgent()  # Initialize AI agent

    async def analyze_and_decide(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze case data and decide on next actions.
        
        Args:
            case_data: The case data to analyze
            
        Returns:
            Dict containing decisions and recommended actions
        """
        try:
            # Get AI analysis capability
            analyze_capability = await self.registry.get_capability("analyze_case")
            analysis_result = await analyze_capability(case_data)
            
            # Ensure analysis_result is a dictionary
            if isinstance(analysis_result, str):
                # If it's a string, try to parse it as a structured analysis
                analysis_result = self._parse_analysis_response(analysis_result)

            # Determine required actions based on analysis
            decisions = await self._make_decisions(analysis_result)

            # Get investigation capability if needed
            if decisions["needs_investigation"]:
                investigate_capability = await self.registry.get_capability("investigate_case")
                investigation_result = await investigate_capability(case_data)
                decisions.update({"investigation": investigation_result})

            # Record decision metrics
            await self._record_decision_metrics(case_data["_id"], decisions)

            return decisions

        except Exception as e:
            logger.error(f"Error in decision making for case {case_data.get('_id')}: {e}")
            raise

    def _parse_analysis_response(self, response_text: str) -> Dict[str, Any]:
        """Parse a string response into structured analysis data."""
        try:
            # Extract risk level (assuming it's mentioned in the format "Risk level: X" or similar)
            risk_level = 5  # Default medium risk
            for line in response_text.split('\n'):
                if 'risk level' in line.lower():
                    try:
                        risk_level = int(float(line.split(':')[1].strip().split()[0]))
                    except (ValueError, IndexError):
                        pass

            # Determine if human investigation is needed
            needs_human = (
                'human' in response_text.lower() and 
                ('needed' in response_text.lower() or 'required' in response_text.lower())
            )

            # Extract risk factors
            risk_factors = []
            risk_section = False
            for line in response_text.split('\n'):
                if 'risk factor' in line.lower():
                    risk_section = True
                elif risk_section and line.strip().startswith('-'):
                    risk_factors.append(line.strip()[1:].strip())
                elif risk_section and line.strip() and not line.strip().startswith('-'):
                    risk_section = False

            # Extract recommended actions
            recommendations = []
            action_section = False
            for line in response_text.split('\n'):
                if 'recommend' in line.lower() or 'action' in line.lower():
                    action_section = True
                elif action_section and line.strip().startswith('-'):
                    action = line.strip()[1:].strip()
                    if 'automat' in action.lower():
                        recommendations.append(f"auto_{action.split()[-1].lower()}")
                    else:
                        recommendations.append(f"manual_{action.split()[-1].lower()}")
                elif action_section and line.strip() and not line.strip().startswith('-'):
                    action_section = False

            return {
                "risk_level": risk_level,
                "needs_human": needs_human,
                "risk_factors": risk_factors,
                "recommendations": recommendations
            }

        except Exception as e:
            logger.error(f"Error parsing analysis response: {str(e)}")
            return {
                "risk_level": 8,  # High risk by default if parsing fails
                "needs_human": True,  # Require human investigation if parsing fails
                "risk_factors": ["parsing_failed"],
                "recommendations": ["manual_review"]
            }

    async def _make_decisions(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Make decisions based on case analysis."""
        decisions = {
            "needs_investigation": analysis.get("risk_level", 0) > 7 or analysis.get("needs_human", False),
            "priority": self._calculate_priority(analysis),
            "automated_actions": [],
            "required_human_actions": []
        }

        # Determine automated actions
        if analysis.get("risk_level", 0) <= 3:
            decisions["automated_actions"].append("auto_close")
        elif analysis.get("risk_level", 0) <= 5:
            decisions["automated_actions"].append("auto_monitor")
        else:
            decisions["required_human_actions"].append("manual_review")

        # Add recommended actions from analysis
        if analysis.get("recommendations"):
            decisions["automated_actions"].extend(
                [rec for rec in analysis["recommendations"] if rec.startswith("auto_")]
            )
            decisions["required_human_actions"].extend(
                [rec for rec in analysis["recommendations"] if rec.startswith("manual_")]
            )

        return decisions

    def _calculate_priority(self, analysis: Dict[str, Any]) -> int:
        """Calculate priority level based on analysis results."""
        base_priority = min(int(analysis.get("risk_level", 0) * 1.5), 10)
        
        # Adjust priority based on various factors
        if analysis.get("needs_human", False):
            base_priority = max(base_priority, 7)
        
        if len(analysis.get("risk_factors", [])) > 3:
            base_priority += 1
            
        return min(base_priority, 10)  # Cap at 10

    async def _record_decision_metrics(self, case_id: str, decisions: Dict[str, Any]) -> None:
        """Record metrics about the decisions made."""
        try:
            await self.supabase.upsert_decision_metrics(case_id, decisions)
        except Exception as e:
            logger.error(f"Error recording decision metrics for case {case_id}: {e}")

    async def make_decisions(self, case_id: str, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """Make decisions about a case.

        Args:
            case_id: The case ID
            case_data: The case data

        Returns:
            The decisions made
        """
        try:
            # Analyze the case
            analysis = await self.ai_agent.analyze_case(case_id, case_data)
            
            # Record the analysis metrics
            metrics = {
                "id": str(uuid.uuid4()),
                "case_id": case_id,
                "created_at": datetime.now().isoformat(),
                "decision_type": "analysis",
                "decision_value": json.dumps(analysis),
                "confidence": analysis.get("confidence", 0.0),
                "model": self.ai_agent.model,
                "prompt": analysis.get("prompt", ""),
                "completion": analysis.get("completion", "")
            }
            
            try:
                await self.supabase.upsert_decision_metrics(metrics)
            except Exception as e:
                logger.error(f"Error recording decision metrics for case {case_id}: {e}")
            
            # Return the decisions
            return {
                "needs_investigation": analysis.get("needs_investigation", False),
                "priority": analysis.get("priority", 0),
                "automated_actions": analysis.get("automated_actions", []),
                "required_human_actions": analysis.get("required_human_actions", [])
            }
            
        except Exception as e:
            logger.error(f"Error in decision making for case {case_id}: {e}")
            raise

    async def process_case(self, case_id: str, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a case and make decisions.

        Args:
            case_id: The case ID
            case_data: The case data

        Returns:
            The decisions made
        """
        try:
            # Analyze the case using AI
            analysis = await self.ai_agent.analyze_case(case_id, case_data)
            
            # Record the analysis metrics
            metrics = {
                "id": str(uuid.uuid4()),
                "case_id": case_id,
                "created_at": datetime.now().isoformat(),
                "decision_type": "analysis",
                "decision_value": json.dumps(analysis),
                "confidence": analysis.get("confidence", 0.0),
                "model": self.ai_agent.model,
                "prompt": analysis.get("prompt", ""),
                "completion": analysis.get("completion", "")
            }
            
            try:
                await self.supabase.upsert_decision_metrics(metrics)
            except Exception as e:
                logger.error(f"Error recording decision metrics for case {case_id}: {e}")
            
            # Return the decisions
            return {
                "needs_investigation": analysis.get("needs_investigation", False),
                "priority": analysis.get("priority", 0),
                "automated_actions": analysis.get("automated_actions", []),
                "required_human_actions": analysis.get("required_human_actions", [])
            }
            
        except Exception as e:
            logger.error(f"Error processing case {case_id}: {e}")
            raise
