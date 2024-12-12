import os
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from supabase import create_client, Client
import datetime
import asyncio
import json

load_dotenv()

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime.date, datetime.datetime)):
            return obj.isoformat()
        return super().default(obj)

class SupabaseWrapper:
    def __init__(self):
        url: str = os.getenv("SUPABASE_URL")
        key: str = os.getenv("SUPABASE_KEY")
        if not url or not key:
            raise ValueError("Missing Supabase credentials")
        self.client: Client = create_client(url, key)

    def insert_case(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert a new case into the cases table."""
        return self.client.table('cases').insert(case_data).execute()

    def insert_alerts(self, alerts: List[Dict[str, Any]], case_id: str) -> List[Dict[str, Any]]:
        """Insert alerts for a case into the alerts table."""
        for alert in alerts:
            alert['case_id'] = case_id
        return self.client.table('alerts').insert(alerts).execute()

    def insert_observables(self, observables: List[Dict[str, Any]], alert_id: str) -> List[Dict[str, Any]]:
        """Insert observables for an alert into the observables table."""
        for observable in observables:
            observable['alert_id'] = alert_id
        return self.client.table('observables').insert(observables).execute()

    def insert_analysis(self, analysis_data: Dict[str, Any]) -> Any:
        """Insert analysis results for a case."""
        response = self.client.table('analysis_results').insert(analysis_data).execute()
        return response

    def insert_actions(self, actions: List[Dict[str, Any]], case_id: str) -> List[Dict[str, Any]]:
        """Insert recommended actions for a case."""
        for action in actions:
            action['case_id'] = case_id
        return self.client.table('action_items').insert(actions).execute()

    def get_case_by_external_id(self, external_id: str) -> Dict[str, Any]:
        """Get a case by its external ID."""
        response = self.client.table('cases').select('*').eq('external_id', external_id).execute()
        return response.data[0] if response.data else None

    def get_case(self, case_id: str) -> Dict[str, Any]:
        """Get a case by its ID."""
        response = self.client.table('cases').select('*').eq('id', case_id).execute()
        return response.data[0] if response.data else None

    def update_case(self, case_id: str, case_data: Dict[str, Any]) -> Any:
        """Update an existing case."""
        response = self.client.table('cases').update(case_data).eq('id', case_id).execute()
        return response

    def get_case_alerts(self, case_id: str) -> List[Dict[str, Any]]:
        """Get all alerts for a case."""
        response = self.client.table('alerts').select('*').eq('case_id', case_id).execute()
        return response.data

    def get_alert_observables(self, alert_id: str) -> List[Dict[str, Any]]:
        """Get all observables for an alert."""
        response = self.client.table('observables').select('*').eq('alert_id', alert_id).execute()
        return response.data

    def get_case_analysis(self, case_id: str) -> Dict[str, Any]:
        """Get analysis results for a case."""
        response = self.client.table('analysis_results').select('*').eq('case_id', case_id).execute()
        return response.data[0] if response.data else None

    def get_case_actions(self, case_id: str) -> List[Dict[str, Any]]:
        """Get actions for a case."""
        response = self.client.table('action_items').select('*').eq('case_id', case_id).order('priority').execute()
        return response.data

    async def create_workflow(self, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new workflow record."""
        # Convert datetime objects to ISO format strings
        serialized_data = json.loads(json.dumps(workflow_data, cls=DateTimeEncoder))
        serialized_data['stage_start_time'] = serialized_data['start_time']
        
        response = await self.client.table('workflows').insert(serialized_data).execute()
        return response.data[0] if response.data else None

    async def get_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get workflow by ID."""
        response = await self.client.table('workflows').select('*').eq('id', workflow_id).execute()
        return response.data[0] if response.data else None

    async def update_workflow_stage(self, workflow_id: str, stage: str) -> Dict[str, Any]:
        """Update workflow stage."""
        data = {
            'current_stage': stage,
            'stage_start_time': datetime.datetime.now(),
            'last_updated': datetime.datetime.now()
        }
        response = await self.client.table('workflows').update(data).eq('id', workflow_id).execute()
        return response.data[0] if response.data else None

    async def update_workflow(self, workflow_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a workflow record."""
        serialized_data = json.loads(json.dumps(update_data, cls=DateTimeEncoder))
        response = await self.client.table('workflows').update(serialized_data).eq('id', workflow_id).execute()
        return response.data[0] if response.data else None

    async def complete_workflow(self, workflow_id: str, status: str = 'completed', error: str = None) -> Dict[str, Any]:
        """Mark a workflow as completed or failed."""
        data = {
            'status': status,
            'completion_time': datetime.datetime.now(),
            'last_updated': datetime.datetime.now()
        }
        if error:
            data['error'] = error
        
        response = await self.client.table('workflows').update(data).eq('id', workflow_id).execute()
        return response.data[0] if response.data else None

    async def create_error_log(self, error_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create an error log entry."""
        serialized_data = json.loads(json.dumps(error_data, cls=DateTimeEncoder))
        response = await self.client.table('error_logs').insert(serialized_data).execute()
        return response.data[0] if response.data else None

    async def update_agent_metrics(self, agent_name: str, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Update agent performance metrics."""
        # Check if metrics exist for this agent
        response = await self.client.table('agent_metrics').select('*').eq('agent_name', agent_name).execute()
        
        if response.data:
            # Update existing metrics
            response = await self.client.table('agent_metrics').update(metrics).eq('agent_name', agent_name).execute()
        else:
            # Create new metrics
            metrics['agent_name'] = agent_name
            response = await self.client.table('agent_metrics').insert(metrics).execute()
        
        return response.data[0] if response.data else None

    async def store_agent_error(self, error_data: Dict[str, Any]) -> Dict[str, Any]:
        """Store agent error information."""
        response = await self.client.table('agent_errors').insert(error_data).execute()
        return response.data[0] if response.data else None

    async def store_optimization_recommendations(self, optimization_data: Dict[str, Any]) -> Dict[str, Any]:
        """Store workflow optimization recommendations."""
        response = await self.client.table('workflow_optimizations').insert(optimization_data).execute()
        return response.data[0] if response.data else None

    async def store_stuck_workflow_analysis(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """Store analysis of stuck workflows."""
        response = await self.client.table('stuck_workflow_analysis').insert(analysis_data).execute()
        return response.data[0] if response.data else None

    async def get_agent_errors(self, agent_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent errors for a specific agent."""
        response = await self.client.table('agent_errors').select('*').eq('agent', agent_name).order('timestamp', desc=True).limit(limit).execute()
        return response.data if response.data else []

    async def get_workflow_metrics(self, start_time: datetime.datetime, end_time: datetime.datetime) -> Dict[str, Any]:
        """Get workflow performance metrics for a time period."""
        response = await self.client.table('workflows').select('*').gte('start_time', start_time).lte('start_time', end_time).execute()
        
        if not response.data:
            return {}
        
        workflows = response.data
        total = len(workflows)
        completed = sum(1 for w in workflows if w['status'] == 'completed')
        failed = sum(1 for w in workflows if w['status'] == 'failed')
        avg_completion_time = sum(
            (w['completion_time'] - w['start_time']).total_seconds()
            for w in workflows
            if w['status'] == 'completed' and w['completion_time']
        ) / completed if completed > 0 else 0
        
        return {
            'total_workflows': total,
            'completed': completed,
            'failed': failed,
            'success_rate': completed / total if total > 0 else 0,
            'avg_completion_time': avg_completion_time
        }
