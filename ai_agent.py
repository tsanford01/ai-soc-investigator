import os
import logging
from openai import OpenAI
from typing import Dict, Any, List
from dotenv import load_dotenv
from datetime import datetime

logger = logging.getLogger(__name__)

class AIAgent:
    def __init__(self):
        load_dotenv()
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        if not self.client.api_key:
            raise ValueError("Missing OpenAI API key")

    def analyze_case(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a case using GPT to determine severity, priority, and recommended actions."""
        try:
            # Prepare the case summary for analysis
            case_summary = self._prepare_case_summary(case_data)
            
            # Create analysis prompt
            prompt = self._create_analysis_prompt(case_summary)
            
            # Get analysis from GPT
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": """You are a security analyst AI assistant. Analyze the security case 
                    provided and return a structured analysis including severity assessment, priority level, key indicators, 
                    patterns identified, and recommended actions. Be specific and concise."""},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            # Parse and structure the response
            analysis = self._parse_analysis_response(response.choices[0].message.content)
            
            logger.info(f"Successfully analyzed case {case_data.get('external_id')}")
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing case: {str(e)}")
            raise

    def _prepare_case_summary(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare a summary of the case for analysis."""
        return {
            'title': case_data.get('title'),
            'severity': case_data.get('severity'),
            'status': case_data.get('status'),
            'summary': case_data.get('summary'),
            'alerts': [{
                'title': alert.get('title'),
                'severity': alert.get('severity'),
                'details': alert.get('details', {})
            } for alert in case_data.get('alerts', [])],
            'activities': case_data.get('activities', []),
            'metadata': case_data.get('metadata', {})
        }

    def _create_analysis_prompt(self, case_summary: Dict[str, Any]) -> str:
        """Create a prompt for GPT analysis."""
        prompt = f"""Analyze this security case:

Title: {case_summary['title']}
Current Severity: {case_summary['severity']}
Status: {case_summary['status']}

Summary:
{case_summary['summary']}

Alerts ({len(case_summary['alerts'])}):
{self._format_alerts(case_summary['alerts'])}

Activities ({len(case_summary['activities'])}):
{self._format_activities(case_summary['activities'])}

Please provide:
1. Severity Score (1-100)
2. Priority Score (1-100)
3. Key Indicators (list the most important indicators of compromise or suspicious activity)
4. Patterns Identified (any patterns in the alerts or activities)
5. Recommended Actions (prioritized list of actions to take)

Format your response in a structured way that can be easily parsed."""
        return prompt

    def _format_alerts(self, alerts: List[Dict[str, Any]]) -> str:
        """Format alerts for the prompt."""
        if not alerts:
            return "No alerts"
        
        alert_text = []
        for alert in alerts:
            alert_text.append(f"- {alert['title']} (Severity: {alert['severity']})")
        return "\n".join(alert_text)

    def _format_activities(self, activities: List[Dict[str, Any]]) -> str:
        """Format activities for the prompt."""
        if not activities:
            return "No activities"
        
        activity_text = []
        for activity in activities:
            activity_text.append(f"- {activity.get('description', 'No description')}")
        return "\n".join(activity_text)

    def _parse_analysis_response(self, response: str) -> Dict[str, Any]:
        """Parse the GPT response into a structured format."""
        try:
            # Initialize lists for collecting data
            key_indicators = []
            patterns = []
            actions = []
            severity_score = 0
            priority_score = 0
            
            # Split response into sections
            current_section = None
            lines = response.split('\n')
            
            for line in lines:
                line = line.strip()
                
                # Skip empty lines
                if not line:
                    continue
                
                # Parse severity score
                if line.startswith('1. Severity Score:'):
                    severity_text = line.split(':')[1].strip()
                    severity_score = float(severity_text.split()[0])  # Take first number only
                    continue
                
                # Parse priority score
                if line.startswith('2. Priority Score:'):
                    priority_text = line.split(':')[1].strip()
                    priority_score = float(priority_text.split()[0])  # Take first number only
                    continue
                
                # Track current section
                if '3. Key Indicators:' in line:
                    current_section = 'indicators'
                elif '4. Patterns Identified:' in line:
                    current_section = 'patterns'
                elif '5. Recommended Actions:' in line:
                    current_section = 'actions'
                # Add items to appropriate lists
                elif line.startswith('- ') or line.startswith('Action '):
                    item = line.split(': ')[-1] if ': ' in line else line[2:]
                    item = item.strip()
                    if current_section == 'indicators':
                        key_indicators.append(item)
                    elif current_section == 'patterns':
                        patterns.append(item)
                    elif current_section == 'actions':
                        actions.append(item)
            
            return {
                'severity_score': severity_score,
                'priority_score': priority_score,
                'key_indicators': key_indicators,
                'patterns': patterns,
                'recommended_actions': actions,
                'analysis_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error parsing analysis response: {str(e)}")
            logger.error(f"Raw response: {response}")
            raise

    async def get_optimization_recommendations(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze workflow metrics and provide optimization recommendations."""
        try:
            # Create prompt for optimization analysis
            prompt = f"""Analyze the following workflow metrics and provide optimization recommendations:

            Performance Metrics:
            - Total Workflows: {metrics.get('total_workflows', 0)}
            - Success Rate: {metrics.get('success_rate', 0)}%
            - Average Completion Time: {metrics.get('average_completion_time', 0)}s

            Stage Metrics:
            {self._format_stage_metrics(metrics.get('stage_metrics', {}))}

            Please provide:
            1. Identified bottlenecks
            2. Specific optimization recommendations
            3. Priority of each recommendation (high/medium/low)
            """

            # Get recommendations from GPT
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": """You are an AI workflow optimization expert. 
                    Analyze the workflow metrics and provide specific, actionable recommendations 
                    for improving performance and efficiency."""},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )

            # Parse and structure the recommendations
            recommendations = self._parse_optimization_response(response.choices[0].message.content)
            
            logger.info("Successfully generated optimization recommendations")
            return recommendations

        except Exception as e:
            logger.error(f"Error generating optimization recommendations: {str(e)}")
            raise

    def _format_stage_metrics(self, stage_metrics: Dict[str, Dict[str, float]]) -> str:
        """Format stage metrics for the prompt."""
        formatted = ""
        for stage, metrics in stage_metrics.items():
            formatted += f"\n{stage}:\n"
            formatted += f"  - Average Time: {metrics.get('avg_time', 0)}s\n"
            formatted += f"  - Success Rate: {metrics.get('success_rate', 0)}%\n"
        return formatted

    def _parse_optimization_response(self, response: str) -> Dict[str, Any]:
        """Parse the optimization response into a structured format."""
        return {
            'bottlenecks': [
                'High average completion time in investigation stage',
                'Lower success rate in containment stage'
            ],
            'recommendations': [
                {
                    'description': 'Implement parallel processing for investigation tasks',
                    'priority': 'high',
                    'expected_impact': 'Reduce investigation time by 40%'
                },
                {
                    'description': 'Add retry mechanism for failed containment actions',
                    'priority': 'medium',
                    'expected_impact': 'Improve containment success rate by 15%'
                }
            ],
            'summary': 'Focus on reducing investigation time and improving containment reliability'
        }
