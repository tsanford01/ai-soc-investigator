import os
import uuid
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable, Union, TypedDict
from supabase_client import SupabaseWrapper
from api_client import APIClient
from ai_agent import AIAgent
from slack_notifier import SlackNotifier

logger = logging.getLogger(__name__)

class WorkflowStage(TypedDict):
    start_time: datetime
    status: str

class AgentMetrics(TypedDict):
    success: int
    failure: int
    avg_time: float

class CoordinatorAgent:
    def __init__(self, api_client: APIClient, supabase_client: SupabaseWrapper, ai_agent: AIAgent):
        """Initialize the CoordinatorAgent with required components and configuration.
        
        Args:
            api_client: Client for making API calls
            supabase_client: Client for database operations
            ai_agent: AI agent for analysis and recommendations
            
        Raises:
            ValueError: If any required client is None or improperly configured
        """
        if not api_client:
            raise ValueError("API client is required")
        if not supabase_client:
            raise ValueError("Supabase client is required")
        if not ai_agent:
            raise ValueError("AI agent is required")
            
        self.api_client = api_client
        self.supabase = supabase_client
        self.ai_agent = ai_agent
        self.slack_notifier = SlackNotifier()
        
        # Initialize workflow stages tracking
        self.workflow_stages: Dict[str, WorkflowStage] = {}
        
        # Initialize performance metrics
        self.metrics: Dict[str, AgentMetrics] = {
            'alert_ingestion': {'success': 0, 'failure': 0, 'avg_time': 0},
            'triage': {'success': 0, 'failure': 0, 'avg_time': 0},
            'investigation': {'success': 0, 'failure': 0, 'avg_time': 0},
            'containment': {'success': 0, 'failure': 0, 'avg_time': 0},
            'review': {'success': 0, 'failure': 0, 'avg_time': 0},
            'soc_optimization': {'success': 0, 'failure': 0, 'avg_time': 0}
        }
        
        # Initialize agent status tracking
        self.agent_status: Dict[str, str] = {
            'alert_ingestion': 'ready',
            'triage': 'ready',
            'investigation': 'ready',
            'containment': 'ready',
            'review': 'ready',
            'soc_optimization': 'ready'
        }
        
        # Load and validate optimization thresholds
        try:
            self.thresholds = {
                'execution_time': max(1.0, float(os.getenv('EXECUTION_TIME_THRESHOLD', '30'))),
                'success_rate': min(1.0, max(0.0, float(os.getenv('SUCCESS_RATE_THRESHOLD', '0.95')))),
                'error_threshold': max(1, int(os.getenv('ERROR_THRESHOLD', '3')))
            }
        except ValueError as e:
            logger.error(f"Error parsing environment variables: {e}")
            # Set safe defaults
            self.thresholds = {
                'execution_time': 30.0,
                'success_rate': 0.95,
                'error_threshold': 3
            }
        
        # Error tracking
        self.error_counts = {agent: 0 for agent in self.agent_status.keys()}
        
    async def start_workflow(self, alert_data: Dict[str, Any]) -> str:
        """Start the incident response workflow with a new alert.
        
        Args:
            alert_data: Dictionary containing alert information
            
        Returns:
            str: Workflow ID
            
        Raises:
            ValueError: If alert_data is invalid
            RuntimeError: If workflow creation fails
        """
        if not alert_data:
            raise ValueError("Alert data is required")
        if 'id' not in alert_data:
            raise ValueError("Alert must have an ID")
            
        workflow_id = str(uuid.uuid4())
        start_time = datetime.now()
        
        try:
            # Initialize workflow stage tracking
            self.workflow_stages[workflow_id] = {
                'start_time': start_time,
                'status': 'started'
            }
            
            # Create workflow record
            await self.supabase.create_workflow({
                'id': workflow_id,
                'status': 'started',
                'alert_id': alert_data['id'],
                'start_time': start_time,
                'current_stage': 'alert_ingestion'
            })
            
            logger.info(f"Started new workflow {workflow_id} for alert {alert_data['id']}")
            
            # Start async monitoring of the workflow
            monitor_task = asyncio.create_task(self._monitor_workflow(workflow_id))
            monitor_task.add_done_callback(
                lambda t: logger.error(f"Workflow monitor failed: {t.exception()}") if t.exception() else None
            )
            
            return workflow_id
            
        except Exception as e:
            logger.error(f"Error starting workflow: {str(e)}")
            if workflow_id in self.workflow_stages:
                del self.workflow_stages[workflow_id]
            await self._handle_workflow_error(workflow_id, str(e))
            raise RuntimeError(f"Failed to start workflow: {str(e)}")
    
    async def _monitor_workflow(self, workflow_id: str) -> None:
        """Monitor the progress of a workflow.
        
        Args:
            workflow_id: ID of the workflow to monitor
            
        Raises:
            RuntimeError: If workflow monitoring fails repeatedly
        """
        consecutive_errors = 0
        max_consecutive_errors = 3
        
        while True:
            try:
                workflow = await self.supabase.get_workflow(workflow_id)
                if not workflow:
                    logger.error(f"Workflow {workflow_id} not found")
                    break
                    
                if workflow['status'] in ['completed', 'failed']:
                    logger.info(f"Workflow {workflow_id} finished with status: {workflow['status']}")
                    if workflow_id in self.workflow_stages:
                        del self.workflow_stages[workflow_id]
                    break
                    
                # Check for stuck workflows
                current_time = datetime.now()
                stage_start_time = workflow.get('stage_start_time', current_time)
                if isinstance(stage_start_time, str):
                    stage_start_time = datetime.fromisoformat(stage_start_time.replace('Z', '+00:00'))
                
                time_in_stage = (current_time - stage_start_time).total_seconds()
                if time_in_stage > self.thresholds['execution_time']:
                    await self._handle_stuck_workflow(workflow_id, workflow['current_stage'])
                
                consecutive_errors = 0  # Reset error count on successful check
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                consecutive_errors += 1
                logger.error(f"Error monitoring workflow {workflow_id}: {str(e)}")
                
                if consecutive_errors >= max_consecutive_errors:
                    logger.critical(f"Monitoring failed {max_consecutive_errors} times for workflow {workflow_id}")
                    await self._handle_workflow_error(
                        workflow_id, 
                        f"Monitoring failed after {max_consecutive_errors} attempts: {str(e)}"
                    )
                    break
                
                # Exponential backoff
                await asyncio.sleep(min(30 * (2 ** (consecutive_errors - 1)), 300))
    
    async def _execute_stage(self, stage_name: str, stage_func: Callable[..., Any], *args) -> Any:
        """Execute a workflow stage and track its performance.
        
        Args:
            stage_name: Name of the stage to execute
            stage_func: Function to execute for this stage
            *args: Arguments to pass to the stage function
            
        Returns:
            Any: Result from the stage function
            
        Raises:
            ValueError: If stage_name is invalid
            RuntimeError: If stage execution fails
        """
        if stage_name not in self.agent_status:
            raise ValueError(f"Invalid stage name: {stage_name}")
            
        if not callable(stage_func):
            raise ValueError("stage_func must be callable")
            
        try:
            # Update agent status
            self.agent_status[stage_name] = 'working'
            start_time = datetime.now()
            
            # Execute stage
            result = await stage_func(*args)
            
            # Update metrics
            execution_time = (datetime.now() - start_time).total_seconds()
            await self._update_metrics(stage_name, 'success', execution_time)
            
            # Reset error count on success
            self.error_counts[stage_name] = 0
            self.agent_status[stage_name] = 'ready'
            
            return result
            
        except Exception as e:
            error_msg = f"Stage {stage_name} failed: {str(e)}"
            logger.error(error_msg)
            
            await self._update_metrics(stage_name, 'failure', 0)
            self.agent_status[stage_name] = 'error'
            self.error_counts[stage_name] += 1
            
            if self.error_counts[stage_name] >= self.thresholds['error_threshold']:
                await self._handle_agent_failure(stage_name, str(e))
            
            raise RuntimeError(error_msg) from e
    
    async def _update_metrics(self, stage_name: str, outcome: str, execution_time: float) -> None:
        """Update performance metrics for an agent.
        
        Args:
            stage_name: Name of the stage to update metrics for
            outcome: Either 'success' or 'failure'
            execution_time: Time taken to execute the stage in seconds
            
        Raises:
            ValueError: If stage_name or outcome is invalid
        """
        if stage_name not in self.metrics:
            raise ValueError(f"Invalid stage name: {stage_name}")
        if outcome not in ['success', 'failure']:
            raise ValueError(f"Invalid outcome: {outcome}")
            
        metrics = self.metrics[stage_name]
        
        try:
            if outcome == 'success':
                metrics['success'] += 1
                # Update running average of execution time
                total_executions = metrics['success']
                metrics['avg_time'] = (metrics['avg_time'] * (total_executions - 1) + execution_time) / total_executions
            else:
                metrics['failure'] += 1
            
            # Store metrics in Supabase
            await self.supabase.update_agent_metrics(stage_name, {
                'success_count': metrics['success'],
                'failure_count': metrics['failure'],
                'avg_execution_time': metrics['avg_time'],
                'last_updated': datetime.now()
            })
            
        except Exception as e:
            logger.error(f"Failed to update metrics for {stage_name}: {str(e)}")
            # Don't raise the exception as metrics updates should not break the workflow
    
    async def get_agent_performance(self) -> Dict[str, Dict[str, Union[float, int, str]]]:
        """Get performance metrics for all agents.
        
        Returns:
            Dict containing performance metrics for each agent
        """
        try:
            return {
                agent: {
                    'success_rate': metrics['success'] / (metrics['success'] + metrics['failure']) 
                        if metrics['success'] + metrics['failure'] > 0 else 0,
                    'avg_execution_time': metrics['avg_time'],
                    'total_executions': metrics['success'] + metrics['failure'],
                    'current_status': self.agent_status[agent]
                }
                for agent, metrics in self.metrics.items()
            }
        except Exception as e:
            logger.error(f"Error getting agent performance: {str(e)}")
            return {}
    
    async def optimize_workflow(self) -> Dict[str, Any]:
        """Analyze and optimize the workflow based on performance metrics.
        
        Returns:
            Dict containing optimization recommendations and bottleneck information
            
        Raises:
            RuntimeError: If optimization analysis fails
        """
        try:
            performance = await self.get_agent_performance()
            if not performance:
                return {'status': 'error', 'message': 'No performance data available'}
            
            # Identify bottlenecks
            bottlenecks = [
                agent for agent, metrics in performance.items()
                if metrics['avg_execution_time'] > self.thresholds['execution_time']
                or metrics['success_rate'] < self.thresholds['success_rate']
            ]
            
            # Convert performance metrics to the format expected by AI agent
            metrics = {
                'total_workflows': sum(m['total_executions'] for m in performance.values()),
                'success_rate': sum(m['success_rate'] for m in performance.values()) / len(performance),
                'average_completion_time': sum(m['avg_execution_time'] for m in performance.values()),
                'stage_metrics': {
                    agent: {
                        'avg_time': m['avg_execution_time'],
                        'success_rate': m['success_rate'] * 100  # Convert to percentage
                    }
                    for agent, m in performance.items()
                }
            }
            
            # Get optimization recommendations from AI
            recommendations = await self.ai_agent.get_optimization_recommendations(metrics)
            
            if recommendations.get('bottlenecks'):
                # Store recommendations
                await self.supabase.store_optimization_recommendations({
                    'timestamp': datetime.now(),
                    'bottlenecks': recommendations['bottlenecks'],
                    'recommendations': recommendations['recommendations'],
                    'performance_metrics': performance
                })
                
                # Notify about optimization recommendations
                await self._notify_optimization_recommendations(
                    recommendations['bottlenecks'],
                    recommendations
                )
                
                return recommendations
            
            return {'status': 'optimal', 'message': 'No bottlenecks detected'}
            
        except Exception as e:
            error_msg = f"Failed to optimize workflow: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e
    
    async def _handle_agent_failure(self, agent_name: str, error: str) -> None:
        """Handle agent failures and implement recovery strategies.
        
        Args:
            agent_name: Name of the failed agent
            error: Error message
        """
        logger.error(f"Agent failure: {agent_name} - {error}")
        
        try:
            # Store error in Supabase
            await self.supabase.store_agent_error({
                'agent': agent_name,
                'error': str(error),
                'timestamp': datetime.now(),
                'error_count': self.error_counts[agent_name]
            })
            
            # Get recovery strategy from AI
            recovery_strategy = await self.ai_agent.get_recovery_strategy(
                agent_name=agent_name,
                error=error,
                error_count=self.error_counts[agent_name]
            )
            
            # Notify about agent failure
            await self._notify_agent_failure(agent_name, error, recovery_strategy)
            
        except Exception as e:
            logger.error(f"Error handling agent failure for {agent_name}: {str(e)}")
            # We don't raise here as this is already an error handler
    
    async def _handle_stuck_workflow(self, workflow_id: str, current_stage: str) -> None:
        """Handle workflows that are stuck in a particular stage.
        
        Args:
            workflow_id: ID of the stuck workflow
            current_stage: Current stage where the workflow is stuck
        """
        logger.warning(f"Workflow {workflow_id} stuck in stage {current_stage}")
        
        try:
            if workflow_id not in self.workflow_stages:
                logger.error(f"No stage information found for workflow {workflow_id}")
                return
                
            # Get analysis from AI
            analysis = await self.ai_agent.analyze_stuck_workflow(
                workflow_id=workflow_id,
                current_stage=current_stage,
                time_in_stage=(datetime.now() - self.workflow_stages[workflow_id]['start_time']).total_seconds()
            )
            
            # Store analysis
            await self.supabase.store_stuck_workflow_analysis({
                'workflow_id': workflow_id,
                'stage': current_stage,
                'analysis': analysis,
                'timestamp': datetime.now()
            })
            
            # Notify about stuck workflow
            await self._notify_stuck_workflow(workflow_id, current_stage, analysis)
            
        except Exception as e:
            logger.error(f"Error handling stuck workflow {workflow_id}: {str(e)}")
            await self._handle_workflow_error(workflow_id, f"Failed to handle stuck workflow: {str(e)}")
    
    async def _handle_workflow_error(self, workflow_id: str, error_message: str) -> None:
        """Handle workflow errors by updating the workflow status and logging the error.
        
        Args:
            workflow_id: ID of the failed workflow
            error_message: Error message to log
        """
        try:
            await self.supabase.update_workflow(workflow_id, {
                'status': 'error',
                'error_message': error_message,
                'updated_at': datetime.now()
            })
            
            await self.supabase.create_error_log({
                'workflow_id': workflow_id,
                'error_message': error_message,
                'timestamp': datetime.now()
            })
            
            logger.error(f"Workflow {workflow_id} failed: {error_message}")
            
            # Clean up workflow stages
            if workflow_id in self.workflow_stages:
                del self.workflow_stages[workflow_id]
            
            # Notify about the error via Slack
            await self.slack_notifier.send_message(
                f"🚨 Error in workflow {workflow_id}: {error_message}"
            )
            
        except Exception as e:
            # At this point, we can only log the error as this is our last resort error handler
            logger.critical(f"Critical error while handling workflow error: {str(e)}")
    
    async def _notify_optimization_recommendations(
        self, 
        bottlenecks: List[str], 
        recommendations: Dict[str, Any]
    ) -> None:
        """Notify about optimization recommendations.
        
        Args:
            bottlenecks: List of identified bottlenecks
            recommendations: Dictionary containing detailed recommendations
        """
        try:
            message = ["🔄 Workflow Optimization Recommendations:", "", "Bottlenecks Identified:"]
            
            for bottleneck in bottlenecks:
                message.append(f"- {bottleneck}")
                
            message.extend(["", "Recommendations:"])
            for rec in recommendations.get('recommendations', []):
                rec_line = f"- [{rec.get('priority', 'MEDIUM').upper()}] {rec.get('description', 'No description')}"
                if rec.get('expected_impact'):
                    rec_line += f" (Expected Impact: {rec['expected_impact']})"
                message.append(rec_line)
                
            if recommendations.get('summary'):
                message.extend(["", f"Summary: {recommendations['summary']}"])
            
            await self.slack_notifier.send_message("\n".join(message))
            
        except Exception as e:
            logger.error(f"Error sending optimization recommendations: {str(e)}")
    
    async def _notify_agent_failure(
        self, 
        agent_name: str, 
        error: str, 
        recovery_strategy: Dict[str, Any]
    ) -> None:
        """Notify about agent failures.
        
        Args:
            agent_name: Name of the failed agent
            error: Error message
            recovery_strategy: Dictionary containing recovery recommendations
        """
        try:
            message = [
                "⚠️ Agent Failure Alert",
                "",
                f"Agent: {agent_name}",
                f"Error: {error}",
                "",
                "Recovery Strategy:",
                recovery_strategy.get('recommendation', 'No recovery strategy available')
            ]
            
            await self.slack_notifier.notify_high_priority_case(
                case_data={'title': f'Agent Failure: {agent_name}'},
                analysis_data={
                    'severity_score': 8, 
                    'priority_score': 9, 
                    'key_indicators': [error]
                }
            )
            
        except Exception as e:
            logger.error(f"Error notifying agent failure: {str(e)}")
    
    async def _notify_stuck_workflow(
        self, 
        workflow_id: str, 
        current_stage: str, 
        analysis: Dict[str, Any]
    ) -> None:
        """Notify about stuck workflows.
        
        Args:
            workflow_id: ID of the stuck workflow
            current_stage: Current stage where the workflow is stuck
            analysis: Dictionary containing workflow analysis
        """
        try:
            message = [
                "⚠️ Stuck Workflow Alert",
                "",
                f"Workflow ID: {workflow_id}",
                f"Current Stage: {current_stage}",
                "",
                "Analysis:",
                analysis.get('diagnosis', 'No diagnosis available'),
                "",
                "Recommended Action:",
                analysis.get('recommendation', 'No recommendation available')
            ]
            
            await self.slack_notifier.notify_high_priority_case(
                case_data={'title': f'Stuck Workflow: {workflow_id}'},
                analysis_data={
                    'severity_score': 7, 
                    'priority_score': 8, 
                    'key_indicators': [current_stage]
                }
            )
            
        except Exception as e:
            logger.error(f"Error notifying stuck workflow: {str(e)}")
