import os
from datetime import datetime
import logging
from dotenv import load_dotenv
from auth import authenticate
from api_client import APIClient
from case_collector import CaseCollector
from supabase_client import SupabaseWrapper
from ai_agent import AIAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    # Load environment variables
    load_dotenv()
    
    try:
        # Authenticate and initialize components
        logger.info("Authenticating...")
        api_client = authenticate()
        supabase_client = SupabaseWrapper()
        ai_agent = AIAgent()
        logger.info("Successfully authenticated!")
        
        # Create collector
        collector = CaseCollector(api_client, supabase_client, ai_agent)
        
        # Test multiple case collection
        logger.info("Fetching and analyzing recent cases...")
        results = collector.collect_multiple_cases(limit=5)
        
        logger.info(f"Successfully collected and analyzed {len(results)} cases")
        
        # Print summary of collected cases
        for case in results:
            logger.info(f"\nCase Summary:")
            logger.info(f"Title: {case['title']}")
            logger.info(f"Severity: {case['severity']}")
            logger.info(f"Status: {case['status']}")
            logger.info(f"Number of alerts: {len(case['alerts'])}")
            logger.info(f"Number of activities: {len(case['activities'])}")
            
            # Get analysis results from Supabase
            case_data = collector.supabase.get_case_by_external_id(case['external_id'])
            if case_data:
                analysis = collector.supabase.get_case_analysis(case_data['id'])
                if analysis:
                    logger.info("\nAI Analysis:")
                    logger.info(f"Severity Score: {analysis['severity_score']}")
                    logger.info(f"Priority Score: {analysis['priority_score']}")
                    logger.info("Key Indicators:")
                    for indicator in analysis['key_indicators']:
                        logger.info(f"- {indicator}")
                    logger.info("\nRecommended Actions:")
                    actions = collector.supabase.get_case_actions(case_data['id'])
                    for action in actions:
                        logger.info(f"[{action['priority']}] {action['description']}")
            
    except Exception as e:
        logger.error(f"Error in test: {str(e)}")
        return

if __name__ == "__main__":
    main()
