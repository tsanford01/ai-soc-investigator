import datetime
from typing import Dict, Any, List, Optional
import uuid

class MockSupabase:
    def __init__(self):
        self.workflows = {}
        self.error_logs = {}
        self.agent_metrics = {}

    async def create_workflow(self, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new workflow record."""
        workflow_id = str(uuid.uuid4())
        self.workflows[workflow_id] = {**workflow_data, 'id': workflow_id}
        return self.workflows[workflow_id]

    async def update_workflow(self, workflow_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a workflow record."""
        if workflow_id not in self.workflows:
            return None
        self.workflows[workflow_id].update(update_data)
        return self.workflows[workflow_id]

    async def create_error_log(self, error_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create an error log entry."""
        error_id = str(uuid.uuid4())
        self.error_logs[error_id] = {**error_data, 'id': error_id}
        return self.error_logs[error_id]

    async def get_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get a workflow by ID."""
        return self.workflows.get(workflow_id)

    async def update_agent_metrics(self, agent_name: str, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Update agent performance metrics."""
        if agent_name not in self.agent_metrics:
            self.agent_metrics[agent_name] = {}
        self.agent_metrics[agent_name].update(metrics)
        return self.agent_metrics[agent_name]

    async def get_workflow_metrics(self, start_time: datetime.datetime, end_time: datetime.datetime) -> Dict[str, Any]:
        """Get workflow metrics for a time period."""
        return {
            'total_workflows': len(self.workflows),
            'successful_workflows': len([w for w in self.workflows.values() if w.get('status') == 'completed']),
            'failed_workflows': len([w for w in self.workflows.values() if w.get('status') == 'error']),
            'average_completion_time': 120.0,  # Mock 2 minutes average
            'stage_metrics': {
                'alert_ingestion': {'avg_time': 20.0, 'success_rate': 100.0},
                'triage': {'avg_time': 25.0, 'success_rate': 100.0},
                'investigation': {'avg_time': 35.0, 'success_rate': 100.0},
                'containment': {'avg_time': 25.0, 'success_rate': 100.0},
                'review': {'avg_time': 15.0, 'success_rate': 100.0}
            }
        }

    async def store_optimization_recommendations(self, recommendations: Dict[str, Any]) -> Dict[str, Any]:
        """Store optimization recommendations."""
        recommendation_id = str(uuid.uuid4())
        return {'id': recommendation_id, **recommendations}
