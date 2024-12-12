import os
import asyncio
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
from auth import AuthManager
from api_client import APIClient
from mock_supabase import MockSupabase
from ai_agent import AIAgent
from coordinator_agent import CoordinatorAgent
import test_config  # Import test configuration

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_coordinator():
    try:
        # Initialize components
        auth_manager = AuthManager()
        api_client = APIClient(auth_manager)
        supabase_client = MockSupabase()  # Use mock instead of real Supabase
        ai_agent = AIAgent()
        
        # Initialize coordinator
        coordinator = CoordinatorAgent(api_client, supabase_client, ai_agent)
        
        # Test alert data
        test_alert = {
            'id': 'TEST-ALERT-001',
            'title': 'Suspicious Network Activity',
            'severity': 'High',
            'source_ip': '192.168.1.100',
            'destination_ip': '203.0.113.100',
            'timestamp': datetime.now().isoformat()
        }
        
        # Start workflow
        logger.info("Starting test workflow...")
        workflow_id = await coordinator.start_workflow(test_alert)
        logger.info(f"Created workflow: {workflow_id}")
        
        # Simulate some agent executions with different outcomes
        stages = ['alert_ingestion', 'triage', 'investigation', 'containment', 'review']
        
        for stage in stages:
            # Simulate successful execution
            logger.info(f"Executing {stage} stage...")
            try:
                await coordinator._execute_stage(
                    stage,
                    lambda: asyncio.sleep(2),  # Simulate work
                )
                logger.info(f"Successfully completed {stage} stage")
            except Exception as e:
                logger.error(f"Error in {stage} stage: {str(e)}")
        
        # Get agent performance metrics
        logger.info("\nAgent Performance Metrics:")
        performance = await coordinator.get_agent_performance()
        for agent, metrics in performance.items():
            logger.info(f"\n{agent}:")
            logger.info(f"Success Rate: {metrics['success_rate']:.2%}")
            logger.info(f"Average Execution Time: {metrics['avg_execution_time']:.2f}s")
            logger.info(f"Total Executions: {metrics['total_executions']}")
            logger.info(f"Current Status: {metrics['current_status']}")
        
        # Get workflow metrics for the last hour
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=1)
        
        logger.info("\nWorkflow Metrics (Last Hour):")
        workflow_metrics = await supabase_client.get_workflow_metrics(start_time, end_time)
        logger.info(f"Total Workflows: {workflow_metrics.get('total_workflows', 0)}")
        logger.info(f"Completed: {workflow_metrics.get('completed', 0)}")
        logger.info(f"Failed: {workflow_metrics.get('failed', 0)}")
        logger.info(f"Success Rate: {workflow_metrics.get('success_rate', 0):.2%}")
        logger.info(f"Average Completion Time: {workflow_metrics.get('avg_completion_time', 0):.2f}s")
        
        # Get optimization recommendations
        logger.info("\nChecking for possible optimizations...")
        recommendations = await coordinator.optimize_workflow()
        if recommendations.get('status') == 'optimal':
            logger.info("No optimizations needed - workflow is performing optimally")
        else:
            logger.info("Optimization Recommendations:")
            logger.info("\nbottlenecks:")
            for bottleneck in recommendations['bottlenecks']:
                logger.info(f"- {bottleneck}")
                
            logger.info("\nrecommendations:")
            for rec in recommendations['recommendations']:
                logger.info(f"- [{rec['priority'].upper()}] {rec['description']}")
                if 'expected_impact' in rec:
                    logger.info(f"  Expected Impact: {rec['expected_impact']}")
                    
            logger.info(f"\nSummary: {recommendations['summary']}")
        
    except Exception as e:
        logger.error(f"Error in test: {str(e)}")
        raise

if __name__ == "__main__":
    load_dotenv()
    asyncio.run(test_coordinator())
