import os
import uuid
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable, Union, TypedDict, NoReturn
from supabase_client import SupabaseWrapper
from api_client import APIClient
from ai_agent import AIAgent, CaseAnalysis
from slack_notifier import SlackNotifier
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class WorkflowStage(TypedDict):
    start_time: datetime
    status: str

class AgentMetrics(TypedDict):
    success: int
    failure: int
    avg_time: float

class StageConfig(BaseModel):
    """Configuration for a workflow stage."""
    name: str
    timeout: float = Field(default=300.0, gt=0.0)  # timeout in seconds
    max_retries: int = Field(default=3, ge=0)
    backoff_factor: float = Field(default=1.5, gt=1.0)

class CoordinatorAgent:
    """Agent responsible for coordinating the case investigation workflow."""

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
        
        # Initialize stage configurations
        self.stage_configs: Dict[str, StageConfig] = {
            'alert_ingestion': StageConfig(name='alert_ingestion', timeout=60.0),
            'triage': StageConfig(name='triage', timeout=120.0),
            'investigation': StageConfig(name='investigation', timeout=300.0),
            'containment': StageConfig(name='containment', timeout=180.0),
            'review': StageConfig(name='review', timeout=120.0),
            'soc_optimization': StageConfig(name='soc_optimization', timeout=300.0)
        }
        
        # Initialize performance metrics
        self.metrics: Dict[str, AgentMetrics] = {
            stage: {'success': 0, 'failure': 0, 'avg_time': 0}
            for stage in self.stage_configs.keys()
        }
        
        # Initialize agent status tracking
        self.agent_status: Dict[str, str] = {
            stage: 'ready' for stage in self.stage_configs.keys()
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
        self.error_counts = {stage: 0 for stage in self.stage_configs.keys()}
        
        # Async primitives
        self._shutdown_event = asyncio.Event()
        self._case_queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()
        self._tasks: List[asyncio.Task] = []

    async def start(self) -> None:
        """Start the coordinator agent and its worker tasks."""
        logger.info("Starting Coordinator Agent...")
        
        # Create worker tasks
        self._tasks = [
            asyncio.create_task(self._process_cases()),
            asyncio.create_task(self._monitor_metrics()),
            asyncio.create_task(self._cleanup_stale_stages())
        ]
        
        try:
            # Wait for shutdown signal
            await self._shutdown_event.wait()
        finally:
            await self.shutdown()

    async def shutdown(self) -> None:
        """Gracefully shut down the coordinator agent."""
        logger.info("Shutting down Coordinator Agent...")
        
        # Cancel all tasks
        for task in self._tasks:
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self._tasks, return_exceptions=True)
        
        # Close clients
        await self.api_client.close()
        await self.supabase.close()
        
        logger.info("Coordinator Agent shutdown complete")

    async def _process_cases(self) -> None:
        """Process cases from the queue."""
        while True:
            try:
                case = await self._case_queue.get()
                await self._process_single_case(case)
                self._case_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing case: {str(e)}")
                await asyncio.sleep(5)  # Brief delay before retrying

    async def _process_single_case(self, case: Dict[str, Any]) -> None:
        """Process a single case through all stages.
        
        Args:
            case: Case data to process
            
        Raises:
            RuntimeError: If case processing fails
        """
        case_id = case.get('external_id', 'unknown')
        logger.info(f"Processing case {case_id}")
        
        try:
            # Execute stages in sequence
            stages = ['alert_ingestion', 'triage', 'investigation', 'containment', 'review']
            for stage in stages:
                config = self.stage_configs[stage]
                
                # Execute stage with timeout and retries
                for attempt in range(config.max_retries + 1):
                    try:
                        async with asyncio.timeout(config.timeout):
                            await self._execute_stage(stage, self._get_stage_handler(stage), case)
                        break  # Stage completed successfully
                    except asyncio.TimeoutError:
                        logger.warning(f"Stage {stage} timed out for case {case_id}")
                        if attempt == config.max_retries:
                            raise
                        await asyncio.sleep(config.backoff_factor ** attempt)
                    except Exception as e:
                        logger.error(f"Stage {stage} failed for case {case_id}: {str(e)}")
                        if attempt == config.max_retries:
                            raise
                        await asyncio.sleep(config.backoff_factor ** attempt)
            
            logger.info(f"Successfully processed case {case_id}")
            
        except Exception as e:
            logger.error(f"Failed to process case {case_id}: {str(e)}")
            await self._handle_case_failure(case, str(e))
            raise RuntimeError(f"Case processing failed: {str(e)}") from e

    def _get_stage_handler(self, stage: str) -> Callable:
        """Get the handler function for a stage.
        
        Args:
            stage: Stage name
            
        Returns:
            Callable: Stage handler function
            
        Raises:
            ValueError: If stage is invalid
        """
        handlers = {
            'alert_ingestion': self._handle_alert_ingestion,
            'triage': self._handle_triage,
            'investigation': self._handle_investigation,
            'containment': self._handle_containment,
            'review': self._handle_review
        }
        
        handler = handlers.get(stage)
        if not handler:
            raise ValueError(f"Invalid stage: {stage}")
        return handler

    async def _monitor_metrics(self) -> None:
        """Monitor and analyze agent performance metrics."""
        while True:
            try:
                await self._analyze_performance()
                await asyncio.sleep(300)  # Check every 5 minutes
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error monitoring metrics: {str(e)}")
                await asyncio.sleep(60)  # Brief delay before retrying

    async def _cleanup_stale_stages(self) -> None:
        """Clean up stale workflow stages."""
        while True:
            try:
                now = datetime.now()
                stale_stages = []
                
                for stage_id, stage in self.workflow_stages.items():
                    if (now - stage['start_time']).total_seconds() > 3600:  # 1 hour timeout
                        stale_stages.append(stage_id)
                
                for stage_id in stale_stages:
                    await self._handle_stage_timeout(stage_id)
                    del self.workflow_stages[stage_id]
                
                await asyncio.sleep(300)  # Check every 5 minutes
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error cleaning up stages: {str(e)}")
                await asyncio.sleep(60)  # Brief delay before retrying

    async def _handle_stage_timeout(self, stage_id: str) -> None:
        """Handle a stage timeout.
        
        Args:
            stage_id: ID of the timed out stage
        """
        try:
            stage = self.workflow_stages.get(stage_id)
            if not stage:
                return
                
            logger.warning(f"Stage {stage_id} timed out")
            
            # Update metrics
            stage_name = stage.get('name', 'unknown')
            if stage_name in self.metrics:
                self.metrics[stage_name]['failure'] += 1
            
            # Notify about timeout
            await self.slack_notifier.send_alert(
                f"Stage {stage_id} ({stage_name}) timed out after 1 hour",
                severity="warning"
            )
            
        except Exception as e:
            logger.error(f"Error handling stage timeout: {str(e)}")

    async def _analyze_performance(self) -> None:
        """Analyze agent performance and optimize if needed."""
        try:
            # Calculate success rates and average times
            for stage, metrics in self.metrics.items():
                total = metrics['success'] + metrics['failure']
                if total > 0:
                    success_rate = metrics['success'] / total
                    if success_rate < self.thresholds['success_rate']:
                        await self._optimize_stage(stage)
                        
                    if metrics['avg_time'] > self.thresholds['execution_time']:
                        await self._optimize_stage(stage, focus='performance')
                        
        except Exception as e:
            logger.error(f"Error analyzing performance: {str(e)}")

    async def _optimize_stage(self, stage: str, focus: str = 'reliability') -> None:
        """Optimize a workflow stage.
        
        Args:
            stage: Stage to optimize
            focus: Optimization focus ('reliability' or 'performance')
        """
        try:
            logger.info(f"Optimizing stage {stage} for {focus}")
            
            # Get stage metrics
            metrics = self.metrics[stage]
            
            # Get optimization recommendations
            recommendations = await self.ai_agent.get_optimization_recommendations({
                'stage': stage,
                'focus': focus,
                'metrics': metrics
            })
            
            # Apply recommendations
            config = self.stage_configs[stage]
            if focus == 'reliability':
                config.max_retries += 1
                config.backoff_factor *= 1.2
            else:  # performance
                config.timeout *= 0.8
            
            # Log optimization
            logger.info(f"Applied optimization to {stage}: {recommendations}")
            
            # Notify about optimization
            await self.slack_notifier.send_message(
                f"Optimized {stage} stage for {focus}. New configuration: {config}"
            )
            
        except Exception as e:
            logger.error(f"Error optimizing stage {stage}: {str(e)}")

    async def _handle_case_failure(self, case: Dict[str, Any], error: str) -> None:
        """Handle a case processing failure.
        
        Args:
            case: Failed case data
            error: Error message
        """
        try:
            case_id = case.get('external_id', 'unknown')
            
            # Update case status
            await self.supabase.table('cases').update({
                'status': 'failed',
                'error_message': error,
                'modified_at': datetime.now().isoformat()
            }).eq('external_id', case_id).execute()
            
            # Send notification
            await self.slack_notifier.send_alert(
                f"Case {case_id} processing failed: {error}",
                severity="error"
            )
            
        except Exception as e:
            logger.error(f"Error handling case failure: {str(e)}")

    def _handle_shutdown(self, signum: int, frame: Any) -> None:
        """Handle shutdown signal.
        
        Args:
            signum: Signal number
            frame: Current stack frame
        """
        logger.info(f"Received shutdown signal {signum}")
        self._shutdown_event.set()
