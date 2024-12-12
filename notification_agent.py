from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from typing import Dict, Any, List
from config import settings
from api_client import APIClient
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NotificationAgent:
    def __init__(self):
        self.slack_client = WebClient(token=settings.SLACK_TOKEN)
        self.api_client = APIClient()

    def notify_case_escalation(self, investigation_results: Dict[str, Any]) -> bool:
        """
        Send a notification to Slack about a case that needs human attention.
        Returns True if notification was successful.
        """
        try:
            # Format the message
            blocks = self._format_slack_message(investigation_results)
            
            # Send to Slack
            response = self.slack_client.chat_postMessage(
                channel=settings.SLACK_CHANNEL,
                text=f"Security Case Escalation: Case #{investigation_results['ticket_id']}",
                blocks=blocks
            )
            
            if response["ok"]:
                # Update case with escalation information
                case_id = investigation_results["case_id"]
                self._update_case_escalation(case_id, investigation_results["risk_factors"])
                logger.info(f"Successfully notified about case {case_id}")
                return True
            
            return False

        except SlackApiError as e:
            logger.error(f"Error sending Slack notification: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error in notification process: {str(e)}")
            return False

    def _format_slack_message(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Format the investigation results into Slack blocks."""
        severity_emoji = {
            "Critical": "🔴",
            "High": "🟠",
            "Medium": "🟡",
            "Low": "🔵"
        }

        severity = results.get("severity", "Unknown")
        emoji = severity_emoji.get(severity, "⚪")
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji} Security Case Requires Attention"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Case ID:*\n#{results['ticket_id']}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Severity:*\n{severity}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Score:*\n{results['score']}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Alert Count:*\n{results['alert_count']}"
                    }
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Risk Factors:*\n" + "\n".join(f"• {factor}" for factor in results['risk_factors'])
                }
            }
        ]

        if results.get("kill_chain_stages"):
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Kill Chain Stages:*\n" + "\n".join(f"• {stage}" for stage in results['kill_chain_stages'])
                }
            })

        # Add case summary if available
        if results.get("summary"):
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Case Summary:*\n" + results["summary"][:1000] + "..."  # Truncate long summaries
                }
            })

        return blocks

    def _update_case_escalation(self, case_id: str, risk_factors: List[str]) -> None:
        """Update the case with escalation information."""
        escalation_comment = (
            "Case automatically escalated for human review.\n"
            f"Risk Factors:\n" + "\n".join(f"- {factor}" for factor in risk_factors)
        )
        
        # Update case status and add comment
        self.api_client.update_case(
            case_id=case_id,
            status="Escalated",
            tags=["auto-escalated"]
        )
        self.api_client.add_case_comment(case_id, escalation_comment)
