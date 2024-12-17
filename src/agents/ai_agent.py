"""AI agent for analyzing security cases."""
import os
import logging
from openai import AsyncOpenAI
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

class AIAgent:
    """AI agent for analyzing security cases using GPT-4."""

    def __init__(self):
        """Initialize the AI agent."""
        self.model = "gpt-4"
        self.system_prompt = """You are a security analyst AI assistant. Analyze the security case 
                    provided and return a structured analysis including severity assessment, priority level, key indicators, 
                    patterns identified, and recommended actions. Focus on:
                    1. Risk level (0-10)
                    2. Whether human investigation is needed
                    3. Risk factors identified
                    4. Recommended automated and manual actions
                    Be specific and concise."""

    async def analyze_case(self, case_id: str, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a case using AI.

        Args:
            case_id: The case ID
            case_data: The case data

        Returns:
            The analysis results
        """
        # Format the case data for analysis
        prompt = self._format_case_prompt(case_data)
        
        try:
            # Get completion from OpenAI
            async with AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY")) as client:
                completion = await client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=1000
                )
            
            # Extract the completion text
            completion_text = completion.choices[0].message.content
            
            # Parse the completion into structured data
            analysis = self._parse_completion(completion_text)
            
            # Add metadata
            analysis["prompt"] = prompt
            analysis["completion"] = completion_text
            analysis["confidence"] = 0.8  # TODO: Implement proper confidence scoring
            
            logger.info(f"Successfully analyzed case {case_id}")
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing case {case_id}: {e}")
            raise

    def _format_case_prompt(self, case_data: Dict[str, Any]) -> str:
        """Create a prompt for AI analysis."""
        return f"""Analyze this security case:
        Case ID: {case_data.get('_id')}
        Title: {case_data.get('name')}
        Severity: {case_data.get('severity')}
        Score: {case_data.get('score')}
        Status: {case_data.get('status')}
        Size: {case_data.get('size')}
        Created At: {datetime.fromtimestamp(case_data.get('created_at', 0)/1000).isoformat()}
        
        Provide a structured analysis of the case focusing on:
        1. Risk level (0-10)
        2. Whether human investigation is needed
        3. Risk factors identified
        4. Recommended automated and manual actions"""

    def _parse_completion(self, completion_text: str) -> Dict[str, Any]:
        """Parse AI completion into structured data."""
        try:
            # Extract risk level (assuming it's mentioned in the format "Risk level: X" or similar)
            risk_level = 5  # Default medium risk
            for line in completion_text.split('\n'):
                if 'risk level' in line.lower():
                    try:
                        risk_level = int(float(line.split(':')[1].strip().split()[0]))
                    except (ValueError, IndexError):
                        pass

            # Determine if human investigation is needed
            needs_human = (
                'human' in completion_text.lower() and 
                ('needed' in completion_text.lower() or 'required' in completion_text.lower())
            )

            # Extract risk factors
            risk_factors = []
            risk_section = False
            for line in completion_text.split('\n'):
                if 'risk factor' in line.lower():
                    risk_section = True
                elif risk_section and line.strip().startswith('-'):
                    risk_factors.append(line.strip()[1:].strip())
                elif risk_section and line.strip() and not line.strip().startswith('-'):
                    risk_section = False

            # Extract recommended actions
            recommendations = []
            action_section = False
            for line in completion_text.split('\n'):
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
            logger.error(f"Error parsing AI completion: {str(e)}")
            return {
                "risk_level": 8,  # High risk by default if parsing fails
                "needs_human": True,  # Require human investigation if parsing fails
                "risk_factors": ["parsing_failed"],
                "recommendations": ["manual_review"]
            }
