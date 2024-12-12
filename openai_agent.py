from typing import Dict, Any, List
import openai
from config import settings
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OpenAIAgent:
    def __init__(self):
        openai.api_key = settings.OPENAI_API_KEY
        self.model = settings.OPENAI_MODEL

    async def analyze_case(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze case data using OpenAI to determine risk level and recommendations.
        """
        try:
            # Prepare the prompt
            prompt = self._create_analysis_prompt(case_data)
            
            # Call OpenAI API
            response = await openai.ChatCompletion.acreate(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            # Parse the response
            analysis = self._parse_analysis_response(response.choices[0].message.content)
            return analysis
            
        except Exception as e:
            logger.error(f"Error in OpenAI analysis: {str(e)}")
            raise

    def _get_system_prompt(self) -> str:
        return """You are an expert security analyst AI assistant. Your task is to:
1. Analyze security case data including alerts, kill chain information, and observables
2. Identify risk factors and potential threats
3. Determine if human intervention is needed
4. Provide clear recommendations

Format your response as a JSON object with the following structure:
{
    "risk_level": "high|medium|low",
    "needs_human": true|false,
    "risk_factors": ["list of risk factors"],
    "recommendations": ["list of recommendations"],
    "analysis_summary": "brief analysis summary"
}"""

    def _create_analysis_prompt(self, case_data: Dict[str, Any]) -> str:
        """Create a detailed prompt from case data."""
        alerts = case_data.get("alerts", [])
        kill_chain = case_data.get("kill_chain_stages", [])
        
        prompt = f"""Please analyze this security case:

Case Severity: {case_data.get('severity')}
Case Score: {case_data.get('score')}
Number of Alerts: {len(alerts)}

Kill Chain Stages:
{json.dumps(kill_chain, indent=2)}

Alert Details:
{json.dumps(alerts[:5], indent=2)}  # Show first 5 alerts

Key Considerations:
1. Are there critical kill chain stages present?
2. Is there a pattern in the alerts suggesting a coordinated attack?
3. Does the case score and severity indicate high risk?
4. Are there indicators of active threats?

Please analyze this data and provide your assessment."""

        return prompt

    def _parse_analysis_response(self, response_text: str) -> Dict[str, Any]:
        """Parse the OpenAI response into a structured format."""
        try:
            # Extract JSON from response
            response_json = json.loads(response_text)
            
            # Validate required fields
            required_fields = ["risk_level", "needs_human", "risk_factors", 
                             "recommendations", "analysis_summary"]
            for field in required_fields:
                if field not in response_json:
                    raise ValueError(f"Missing required field: {field}")
            
            return response_json
            
        except json.JSONDecodeError:
            logger.error("Failed to parse OpenAI response as JSON")
            # Provide a fallback response
            return {
                "risk_level": "high",
                "needs_human": True,
                "risk_factors": ["Failed to parse AI analysis"],
                "recommendations": ["Manual review required due to analysis error"],
                "analysis_summary": "Analysis error occurred"
            }
        except Exception as e:
            logger.error(f"Error parsing OpenAI response: {str(e)}")
            raise
