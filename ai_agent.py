import os
import logging
from typing import Dict, Any, List, TypedDict, Optional
from openai import OpenAI
from openai.types.chat import ChatCompletion
from dotenv import load_dotenv
from datetime import datetime
from pydantic import BaseModel, Field
import json

logger = logging.getLogger(__name__)

class CaseAnalysis(BaseModel):
    """Structure for case analysis results."""
    risk_level: int = Field(..., ge=0, le=10)
    needs_investigation: bool
    risk_factors: List[str]
    automated_actions: List[str]
    manual_actions: List[str]
    confidence: float = Field(..., ge=0.0, le=1.0)
    analysis_timestamp: datetime = Field(default_factory=datetime.now)

class AIAgent:
    """AI agent for analyzing security cases using OpenAI's GPT models."""

    def __init__(self):
        """Initialize the AI agent with OpenAI client and configuration.
        
        Raises:
            ValueError: If OpenAI API key is missing
            RuntimeError: If initialization fails
        """
        try:
            load_dotenv()
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("Missing OpenAI API key")
            
            self.client = OpenAI(api_key=api_key)
            self.model = "gpt-4"
            self.system_prompt = """You are a security analyst AI assistant. Analyze the security case 
                provided and return a structured analysis including:
                1. Risk level (0-10)
                2. Whether human investigation is needed (true/false)
                3. Risk factors identified (list)
                4. Recommended automated actions (list)
                5. Recommended manual actions (list)
                Be specific and concise. Format your response as JSON."""
            
            logger.info("AI Agent initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize AI Agent: {str(e)}")
            raise RuntimeError(f"AI Agent initialization failed: {str(e)}") from e

    async def analyze_case(self, case_data: Dict[str, Any]) -> CaseAnalysis:
        """Analyze a case using GPT to determine severity, priority, and recommended actions.
        
        Args:
            case_data: Dictionary containing case information
            
        Returns:
            CaseAnalysis: Structured analysis results
            
        Raises:
            ValueError: If case data is invalid
            RuntimeError: If analysis fails
        """
        if not case_data or not isinstance(case_data, dict):
            raise ValueError("Invalid case data")
            
        try:
            # Prepare the case summary for analysis
            case_summary = self._prepare_case_summary(case_data)
            
            # Create analysis prompt
            prompt = self._create_analysis_prompt(case_summary)
            
            # Get analysis from GPT
            response = await self._get_gpt_analysis(prompt)
            
            # Parse and structure the response
            analysis = self._parse_analysis_response(response)
            
            logger.info(f"Successfully analyzed case {case_data.get('external_id', 'unknown')}")
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing case: {str(e)}")
            raise RuntimeError(f"Case analysis failed: {str(e)}") from e

    def _prepare_case_summary(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare a summary of the case for analysis.
        
        Args:
            case_data: Raw case data
            
        Returns:
            Dict[str, Any]: Structured case summary
            
        Raises:
            ValueError: If required case fields are missing
        """
        required_fields = {"external_id", "title", "severity", "status"}
        missing_fields = required_fields - set(case_data.keys())
        if missing_fields:
            raise ValueError(f"Missing required case fields: {missing_fields}")
            
        return {
            "id": case_data.get("external_id"),
            "title": case_data.get("title"),
            "severity": case_data.get("severity"),
            "status": case_data.get("status"),
            "summary": case_data.get("summary", ""),
            "metadata": case_data.get("metadata", {}),
            "created_at": case_data.get("created_at", ""),
            "tenant": case_data.get("tenant_name", "")
        }

    def _create_analysis_prompt(self, case_summary: Dict[str, Any]) -> str:
        """Create a prompt for GPT analysis.
        
        Args:
            case_summary: Structured case summary
            
        Returns:
            str: Formatted prompt for GPT
        """
        return f"""Please analyze this security case:
        ID: {case_summary['id']}
        Title: {case_summary['title']}
        Severity: {case_summary['severity']}
        Status: {case_summary['status']}
        Summary: {case_summary['summary']}
        Tenant: {case_summary['tenant']}
        
        Provide a structured analysis in JSON format with the following fields:
        - risk_level (0-10)
        - needs_investigation (boolean)
        - risk_factors (list of strings)
        - automated_actions (list of strings)
        - manual_actions (list of strings)
        - confidence (0.0-1.0)"""

    async def _get_gpt_analysis(self, prompt: str) -> ChatCompletion:
        """Get analysis from GPT model.
        
        Args:
            prompt: Analysis prompt
            
        Returns:
            ChatCompletion: GPT response
            
        Raises:
            RuntimeError: If GPT call fails
        """
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            return response
            
        except Exception as e:
            logger.error(f"GPT analysis failed: {str(e)}")
            raise RuntimeError(f"GPT analysis failed: {str(e)}") from e

    def _parse_analysis_response(self, response: ChatCompletion) -> CaseAnalysis:
        """Parse GPT response into structured analysis.
        
        Args:
            response: GPT completion response
            
        Returns:
            CaseAnalysis: Structured analysis results
            
        Raises:
            ValueError: If response parsing fails
        """
        try:
            content = response.choices[0].message.content
            if not content:
                raise ValueError("Empty response from GPT")
                
            # Parse JSON response
            analysis_dict = json.loads(content)
            
            # Validate and create CaseAnalysis object
            return CaseAnalysis(
                risk_level=analysis_dict["risk_level"],
                needs_investigation=analysis_dict["needs_investigation"],
                risk_factors=analysis_dict["risk_factors"],
                automated_actions=analysis_dict["automated_actions"],
                manual_actions=analysis_dict["manual_actions"],
                confidence=analysis_dict.get("confidence", 0.8)
            )
            
        except Exception as e:
            logger.error(f"Failed to parse GPT response: {str(e)}")
            raise ValueError(f"Failed to parse GPT response: {str(e)}") from e
