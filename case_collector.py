from typing import Dict, Any, List
from datetime import datetime
from api_client import APIClient
from supabase_client import SupabaseWrapper
from ai_agent import AIAgent
from slack_notifier import SlackNotifier
import logging

logger = logging.getLogger(__name__)

class CaseCollector:
    def __init__(self, api_client: APIClient, supabase_client: SupabaseWrapper, ai_agent: AIAgent):
        self.api_client = api_client
        self.supabase = supabase_client
        self.ai_agent = ai_agent
        self.slack_notifier = SlackNotifier()
        
    def collect_case_data(self, case_id: str) -> Dict[str, Any]:
        """Collect all data for a specific case and store in Supabase."""
        logger.info(f"Collecting data for case {case_id}")
        
        # Get case details
        case_details = self.api_client.get_case(case_id)
        
        # Get case summary
        case_summary = self.api_client.get_case_summary(case_id)
        
        # Get case alerts
        alerts_response = self.api_client.get_case_alerts(case_id)
        alerts = alerts_response.get('items', [])
        
        # Get case activities
        activities_response = self.api_client.get_case_activities(case_id)
        activities = activities_response.get('items', [])
        
        logger.info(f"Collected case data: {len(alerts)} alerts, {len(activities)} activities")
        
        # Prepare case data for Supabase
        case_data = {
            'external_id': case_id,
            'title': case_details.get('name'),
            'severity': case_details.get('severity'),
            'status': case_details.get('status'),
            'summary': case_summary,
            'metadata': {
                'activities': activities,
                'score': case_details.get('score'),
                'size': case_details.get('size'),
                'created_by': case_details.get('created_by'),
                'modified_by': case_details.get('modified_by'),
                'tenant_name': case_details.get('tenant_name')
            }
        }
        
        # Store in Supabase
        try:
            # Check if case exists
            existing_case = self.supabase.get_case_by_external_id(case_id)
            if existing_case:
                # Update existing case
                case_result = self.supabase.update_case(existing_case['id'], case_data)
                case_uuid = existing_case['id']
                logger.info(f"Updated existing case {case_id} in Supabase")
            else:
                # Insert new case
                case_result = self.supabase.insert_case(case_data)
                case_uuid = case_result.data[0]['id']
                logger.info(f"Inserted new case {case_id} in Supabase")
            
            # Insert alerts
            if alerts:
                alert_data = [{
                    'external_id': alert.get('_id'),
                    'title': alert.get('name'),
                    'severity': alert.get('severity'),
                    'details': alert
                } for alert in alerts]
                self.supabase.insert_alerts(alert_data, case_uuid)
            
            # Analyze case with AI
            try:
                analysis_data = self.ai_agent.analyze_case({
                    **case_data,
                    'alerts': alert_data if alerts else [],
                    'activities': activities
                })
                
                # Store analysis results
                self.supabase.insert_analysis({
                    'case_id': case_uuid,
                    'severity_score': analysis_data['severity_score'],
                    'priority_score': analysis_data['priority_score'],
                    'key_indicators': analysis_data['key_indicators'],
                    'patterns': analysis_data['patterns']
                })
                
                # Store recommended actions
                actions = [{
                    'action_type': 'ai_recommended',
                    'description': action,
                    'priority': f"P{i+1}" if i < 3 else "P3",
                    'status': 'pending'
                } for i, action in enumerate(analysis_data['recommended_actions'])]
                
                if actions:
                    self.supabase.insert_actions(actions, case_uuid)
                
                # Check if human attention is needed based on severity and priority scores
                if (analysis_data.get('severity_score', 0) >= 7 or 
                    analysis_data.get('priority_score', 0) >= 7):
                    self.slack_notifier.notify_high_priority_case(case_data, analysis_data)
                
                logger.info(f"Successfully analyzed case {case_id}")
                
            except Exception as e:
                logger.error(f"Error analyzing case {case_id}: {str(e)}")
            
            logger.info(f"Successfully stored case {case_id} in Supabase")
            
        except Exception as e:
            logger.error(f"Error storing case data in Supabase: {str(e)}")
            raise
        
        return {
            'external_id': case_id,
            'title': case_details.get('name'),
            'severity': case_details.get('severity'),
            'status': case_details.get('status'),
            'alerts': alerts,
            'activities': activities,
            'summary': case_summary
        }
    
    def collect_multiple_cases(
        self,
        limit: int = 5,
        sort_by: str = 'created_at',
        sort_order: str = 'desc'
    ) -> List[Dict[str, Any]]:
        """Collect data for multiple cases and store in Supabase."""
        cases = self.api_client.list_cases(limit=limit, sort_by=sort_by, sort_order=sort_order)
        results = []
        
        for case in cases.get('items', []):
            try:
                case_id = case.get('_id')
                if case_id:
                    result = self.collect_case_data(case_id)
                    results.append(result)
            except Exception as e:
                logger.error(f"Error collecting data for case {case_id}: {str(e)}")
                continue
                
        return results
