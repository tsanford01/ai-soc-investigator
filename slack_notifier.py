import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

class SlackNotifier:
    def __init__(self):
        self.slack_email = "dev-ai-agent-aaaao3etab53lvdr2ehccrrfxa@stellarcyberteam.slack.com"
        self.sender_email = os.getenv("SENDER_EMAIL", "ai.agent@stellarcyber.ai")
        
    def notify_high_priority_case(self, case_data: Dict[str, Any], analysis_data: Dict[str, Any]) -> None:
        """Send a notification to Slack for a high priority case."""
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = self.slack_email
            msg['Subject'] = f"High Priority Case: {case_data.get('title')} [Severity: {analysis_data.get('severity_score')}, Priority: {analysis_data.get('priority_score')}]"
            
            # Create message body
            body = self._create_message_body(case_data, analysis_data)
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email to Slack
            with smtplib.SMTP('localhost') as server:
                server.send_message(msg)
            
            logger.info(f"Successfully sent Slack notification for case {case_data.get('external_id')}")
            
        except Exception as e:
            logger.error(f"Error sending Slack notification: {str(e)}")
            raise
            
    async def send_message(self, message: str) -> None:
        """Send a message to Slack."""
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = self.slack_email
            msg['Subject'] = "AI Agent Notification"
            
            # Add message body
            msg.attach(MIMEText(message, 'plain'))
            
            # Send email to Slack
            with smtplib.SMTP('localhost') as server:
                server.send_message(msg)
            
            logger.info("Successfully sent Slack message")
            
        except Exception as e:
            logger.error(f"Error sending Slack message: {str(e)}")
            # Don't raise the exception - just log it
            # This prevents notification failures from breaking the workflow
            
    def _create_message_body(self, case_data: Dict[str, Any], analysis_data: Dict[str, Any]) -> str:
        """Create a formatted message body for the Slack notification."""
        body = []
        
        # Case details
        body.append("🚨 *High Priority Case Detected* 🚨")
        body.append("")
        body.append(f"*Case Title:* {case_data.get('title')}")
        body.append(f"*Status:* {case_data.get('status')}")
        body.append(f"*Original Severity:* {case_data.get('severity')}")
        body.append("")
        
        # AI Analysis
        body.append("*AI Analysis Results:*")
        body.append(f"- Severity Score: {analysis_data.get('severity_score')}")
        body.append(f"- Priority Score: {analysis_data.get('priority_score')}")
        body.append("")
        
        # Key Indicators
        body.append("*Key Indicators:*")
        for indicator in analysis_data.get('key_indicators', []):
            body.append(f"- {indicator}")
        body.append("")
        
        # Patterns
        if analysis_data.get('patterns'):
            body.append("*Patterns Identified:*")
            for pattern in analysis_data.get('patterns', []):
                body.append(f"- {pattern}")
            body.append("")
        
        # Recommended Actions
        body.append("*Recommended Actions:*")
        for action in analysis_data.get('recommended_actions', []):
            body.append(f"- {action}")
        body.append("")
        
        # Case Link (if available)
        if case_data.get('url'):
            body.append(f"*Case Link:* {case_data.get('url')}")
        
        # Timestamp
        body.append("")
        body.append(f"_Notification sent at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_")
        
        return "\n".join(body)
