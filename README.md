# Security Case Investigation Agent System

This system implements an automated case investigation workflow that monitors security cases, performs analysis, and escalates cases requiring human attention to Slack.

## Components

- **Case Selection Agent**: Identifies and prioritizes cases that need investigation
- **Investigation Agent**: Analyzes case details, alerts, and kill chain information
- **Notification Agent**: Handles Slack notifications for cases requiring human attention
- **Coordinator Agent**: Orchestrates the workflow and optimizes performance of all agents
- **AI Agent**: Provides intelligent analysis and optimization recommendations
- **Slack Notifier**: Handles structured message delivery to Slack

## Architecture

### Coordinator Agent

The Coordinator Agent is the central orchestrator that:

1. **Workflow Management**
   - Initiates and tracks incident response workflows
   - Monitors workflow progress and handles stuck workflows
   - Maintains workflow state and performance metrics

2. **Performance Optimization**
   - Tracks success rates and execution times for each stage
   - Identifies bottlenecks and performance issues
   - Generates optimization recommendations using AI
   - Implements automatic recovery strategies

3. **Error Handling**
   - Manages agent failures with graceful degradation
   - Implements exponential backoff for retries
   - Provides detailed error tracking and reporting
   - Maintains audit logs for all failures

4. **Metrics & Monitoring**
   - Tracks performance metrics for all workflow stages
   - Monitors agent health and status
   - Provides real-time performance insights
   - Generates optimization recommendations

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file with your configuration:
```env
# API Configuration
API_TOKEN=your_api_token
ENVIRONMENT_URL=your_api_url

# Database Configuration
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key

# Slack Configuration
SLACK_TOKEN=your_slack_token
SLACK_CHANNEL=#your-channel

# OpenAI Configuration
OPENAI_API_KEY=your_openai_key

# Performance Thresholds
EXECUTION_TIME_THRESHOLD=30
SUCCESS_RATE_THRESHOLD=0.95
ERROR_THRESHOLD=3
```

3. Initialize the database:
```bash
psql -h your_host -d your_database -U your_user -f schema.sql
```

## Running the System

### Production Mode

Start the coordination agent in production mode:
```bash
python run_coordinator.py
```

### Test Mode

Run the test suite with mock components:
```bash
python test_coordinator.py
```

## Monitoring & Alerts

### Performance Monitoring

The system tracks key metrics:
- Success/failure rates per stage
- Average execution time per stage
- Error counts and types
- Workflow completion rates

### Slack Notifications

The system sends structured notifications for:
1. **High Priority Cases**
   - Severity and priority scores
   - Key risk indicators
   - Direct links to case details

2. **System Alerts**
   - Agent failures and recovery attempts
   - Stuck workflows and diagnosis
   - Performance bottlenecks
   - Optimization recommendations

3. **Error Reports**
   - Detailed error messages
   - Context and stack traces
   - Recovery attempts and status

## Error Handling & Recovery

The system implements a robust error handling strategy:

1. **Graceful Degradation**
   - Continues operation when components fail
   - Implements fallback mechanisms
   - Maintains partial functionality

2. **Automatic Recovery**
   - Implements exponential backoff
   - Uses AI for recovery strategies
   - Tracks error patterns

3. **Resource Cleanup**
   - Proper cleanup of failed workflows
   - Management of system resources
   - Prevention of resource leaks

## Development

### Testing

Run the test suite:
```bash
python -m pytest tests/
```

The test suite includes:
- Unit tests with mock components
- Integration tests with Supabase
- Performance tests
- Error handling tests

### Adding New Components

1. Implement the component interface
2. Add performance tracking
3. Update the coordinator agent
4. Add appropriate tests
5. Update documentation

## Troubleshooting

Common issues and solutions:

1. **Workflow Stuck**
   - Check the workflow status in Supabase
   - Review error logs
   - Check agent status

2. **Performance Issues**
   - Review optimization recommendations
   - Check resource usage
   - Verify API rate limits

3. **Database Issues**
   - Verify connection settings
   - Check table permissions
   - Review migration status

## Usage Examples

### 1. Basic Workflow

```python
from coordinator_agent import CoordinatorAgent
from api_client import APIClient
from ai_agent import AIAgent
from supabase_client import SupabaseWrapper

# Initialize components
api_client = APIClient()
supabase = SupabaseWrapper()
ai_agent = AIAgent()

# Create coordinator
coordinator = CoordinatorAgent(api_client, supabase, ai_agent)

# Start a workflow with an alert
alert_data = {
    'id': 'ALERT-001',
    'title': 'Suspicious Network Activity',
    'severity': 'High',
    'source_ip': '192.168.1.100',
    'destination_ip': '203.0.113.100',
    'timestamp': '2024-12-12T11:58:05-07:00'
}

# Start workflow and get ID
workflow_id = await coordinator.start_workflow(alert_data)
print(f"Started workflow: {workflow_id}")
```

### 2. Performance Monitoring

```python
# Get performance metrics
performance = await coordinator.get_agent_performance()

# Check specific agent metrics
for agent, metrics in performance.items():
    print(f"\nAgent: {agent}")
    print(f"Success Rate: {metrics['success_rate']:.2%}")
    print(f"Avg Execution Time: {metrics['avg_execution_time']:.2f}s")
    print(f"Total Executions: {metrics['total_executions']}")
    print(f"Current Status: {metrics['current_status']}")

# Get optimization recommendations
recommendations = await coordinator.optimize_workflow()
if recommendations['status'] != 'optimal':
    print("\nBottlenecks found:")
    for bottleneck in recommendations['bottlenecks']:
        print(f"- {bottleneck}")
```

### 3. Error Handling

```python
try:
    # Start workflow with invalid data
    workflow_id = await coordinator.start_workflow({})
except ValueError as e:
    print(f"Validation error: {e}")
except RuntimeError as e:
    print(f"Workflow error: {e}")

# Monitor specific workflow
try:
    workflow = await coordinator.supabase.get_workflow(workflow_id)
    if workflow['status'] == 'error':
        print(f"Error: {workflow['error_message']}")
except Exception as e:
    print(f"Monitoring error: {e}")
```

## API Documentation

### CoordinatorAgent

#### Initialization
```python
def __init__(self, api_client: APIClient, supabase_client: SupabaseWrapper, ai_agent: AIAgent)
```
- **Parameters**:
  - `api_client`: Client for making API calls
  - `supabase_client`: Client for database operations
  - `ai_agent`: AI agent for analysis and recommendations
- **Raises**: ValueError if any client is None

#### Workflow Management

```python
async def start_workflow(self, alert_data: Dict[str, Any]) -> str
```
- **Parameters**:
  - `alert_data`: Dictionary containing alert information
- **Returns**: Workflow ID
- **Raises**: 
  - ValueError if alert_data is invalid
  - RuntimeError if workflow creation fails

```python
async def get_agent_performance(self) -> Dict[str, Dict[str, Union[float, int, str]]]
```
- **Returns**: Dictionary of performance metrics per agent
- **Metrics Include**:
  - success_rate: Percentage of successful executions
  - avg_execution_time: Average execution time in seconds
  - total_executions: Total number of executions
  - current_status: Current agent status

```python
async def optimize_workflow(self) -> Dict[str, Any]
```
- **Returns**: Optimization recommendations and bottleneck information
- **Response Format**:
  ```python
  {
      'status': 'optimal' | 'bottleneck_detected',
      'bottlenecks': List[str],
      'recommendations': List[Dict[str, Any]],
      'summary': str
  }
  ```

### AIAgent

```python
def analyze_case(self, case_data: Dict[str, Any]) -> Dict[str, Any]
```
- **Parameters**:
  - `case_data`: Case information to analyze
- **Returns**: Analysis results including severity and recommendations

```python
def get_optimization_recommendations(self, metrics: Dict[str, Any]) -> Dict[str, Any]
```
- **Parameters**:
  - `metrics`: Current performance metrics
- **Returns**: Optimization recommendations

### SlackNotifier

```python
async def send_message(self, message: str) -> None
```
- **Parameters**:
  - `message`: Message to send to Slack
- **Raises**: RuntimeError if sending fails

```python
async def notify_high_priority_case(self, case_data: Dict[str, Any], analysis_data: Dict[str, Any]) -> None
```
- **Parameters**:
  - `case_data`: Case information
  - `analysis_data`: Analysis results
- **Raises**: RuntimeError if notification fails

## Deployment Guide

### Prerequisites

1. **Infrastructure Requirements**:
   - Python 3.9+
   - PostgreSQL 13+
   - Redis (optional, for caching)
   - 2 CPU cores minimum
   - 4GB RAM minimum
   - 20GB disk space

2. **External Services**:
   - Supabase account
   - OpenAI API access
   - Slack workspace with bot permissions
   - Stellar API access

### Deployment Steps

1. **System Preparation**:
   ```bash
   # Update system
   sudo apt-get update
   sudo apt-get upgrade

   # Install dependencies
   sudo apt-get install python3.9 python3.9-venv postgresql-13
   ```

2. **Application Setup**:
   ```bash
   # Create virtual environment
   python3.9 -m venv venv
   source venv/bin/activate

   # Install dependencies
   pip install -r requirements.txt

   # Initialize database
   psql -h localhost -U postgres -f schema.sql
   ```

3. **Configuration**:
   ```bash
   # Copy example env file
   cp .env.example .env

   # Edit configuration
   nano .env

   # Test configuration
   python test_config.py
   ```

4. **Service Setup**:
   ```bash
   # Create service file
   sudo nano /etc/systemd/system/coordinator.service

   # Add service configuration
   [Unit]
   Description=Security Case Coordinator Agent
   After=network.target

   [Service]
   User=coordinator
   WorkingDirectory=/opt/coordinator
   Environment=PYTHONPATH=/opt/coordinator
   ExecStart=/opt/coordinator/venv/bin/python run_coordinator.py
   Restart=always

   [Install]
   WantedBy=multi-user.target

   # Enable and start service
   sudo systemctl enable coordinator
   sudo systemctl start coordinator
   ```

### Monitoring Setup

1. **Logging**:
   ```bash
   # Create log directory
   sudo mkdir /var/log/coordinator
   sudo chown coordinator:coordinator /var/log/coordinator

   # Configure logrotate
   sudo nano /etc/logrotate.d/coordinator
   ```

2. **Metrics**:
   ```bash
   # Install Prometheus and Grafana
   sudo apt-get install prometheus grafana

   # Configure Prometheus
   sudo nano /etc/prometheus/prometheus.yml
   ```

3. **Alerts**:
   ```bash
   # Configure alert rules
   sudo nano /etc/prometheus/alerts.yml

   # Set up Alertmanager
   sudo nano /etc/alertmanager/alertmanager.yml
   ```

### Backup & Recovery

1. **Database Backup**:
   ```bash
   # Create backup script
   nano backup.sh

   #!/bin/bash
   pg_dump -h localhost -U postgres coordinator > /backup/coordinator_$(date +%Y%m%d).sql
   ```

2. **Application Backup**:
   ```bash
   # Backup configuration
   cp .env /backup/env_$(date +%Y%m%d)
   
   # Backup logs
   tar -czf /backup/logs_$(date +%Y%m%d).tar.gz /var/log/coordinator/
   ```

### Health Checks

1. **Service Health**:
   ```bash
   # Check service status
   systemctl status coordinator

   # Check logs
   journalctl -u coordinator -f
   ```

2. **Database Health**:
   ```bash
   # Check connections
   psql -h localhost -U postgres -c "SELECT count(*) FROM pg_stat_activity;"

   # Check table sizes
   psql -h localhost -U postgres -c "\dt+"
   ```

### Scaling Considerations

1. **Vertical Scaling**:
   - Increase CPU/RAM based on metrics
   - Monitor database connection pool
   - Adjust Python garbage collection

2. **Horizontal Scaling**:
   - Deploy multiple coordinator instances
   - Use load balancer
   - Implement Redis for coordination

3. **Database Scaling**:
   - Regular vacuum and reindex
   - Partition large tables
   - Consider read replicas

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

Please make sure to update tests as appropriate.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
