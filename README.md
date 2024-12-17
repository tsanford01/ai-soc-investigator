# Security Case Investigation Agent System

This system implements an automated case investigation workflow that monitors security cases, performs analysis using AI, and manages case escalations. It uses a multi-agent architecture to handle different aspects of case processing and decision making.

## Components

### Core Agents
- **AI Agent**: Provides intelligent case analysis using OpenAI's GPT models
- **Decision Agent**: Makes automated decisions based on case analysis and metrics
- **Case Selection Agent**: Identifies and prioritizes cases for investigation
- **Investigation Agent**: Performs detailed case analysis and evidence collection
- **Notification Agent**: Handles external notifications and alerts
- **Coordinator Agent**: Orchestrates the workflow between all agents

### Supporting Components
- **API Client**: Handles external API communications
- **Supabase Client**: Manages database operations and persistence
- **Authentication**: Handles API and database authentication

## Database Schema

### Cases Table
```sql
- id (UUID): Primary key
- external_id (TEXT): Unique identifier from external system
- title (TEXT): Case title
- severity (TEXT): Case severity level
- status (TEXT): Current case status
- summary (TEXT): Case description
- metadata (JSONB): Additional case metadata
- score (INTEGER): Case priority score
- size (INTEGER): Case size metric
- tenant_name (TEXT): Organization identifier
- closed (INTEGER): Case closure status
- acknowledged (INTEGER): Case acknowledgment status
- created_at (TIMESTAMPTZ): Creation timestamp
- modified_at (TIMESTAMPTZ): Last modification timestamp
```

### Decision Metrics Table
```sql
- id (UUID): Primary key
- case_id (TEXT): Reference to case
- decision_type (TEXT): Type of decision made
- decision_value (JSONB): Decision details
- confidence (FLOAT): Confidence score
- risk_level (TEXT): Assessed risk level
- priority (INTEGER): Priority level
- needs_investigation (BOOLEAN): Investigation flag
- automated_actions (JSONB): List of automated actions
- required_human_actions (JSONB): Required manual actions
- model (TEXT): AI model used
- prompt (TEXT): Analysis prompt
- completion (TEXT): AI response
- created_at (TIMESTAMPTZ): Creation timestamp
```

## Setup Instructions

1. **Clone the Repository**
   ```bash
   git clone <repository-url>
   cd APIs
   ```

2. **Install Dependencies**
   ```bash
   # Install production dependencies
   pip install -r requirements.txt
   
   # For development, also install
   pip install -r requirements-dev.txt
   ```

3. **Environment Setup**
   ```bash
   # Copy the example environment file
   cp setup_env.example.py setup_env.py
   
   # Edit setup_env.py with your credentials:
   - OPENAI_API_KEY: Your OpenAI API key
   - SUPABASE_URL: Your Supabase project URL
   - SUPABASE_KEY: Your Supabase API key
   ```

4. **Database Setup**
   ```bash
   # Run the database migrations in your Supabase SQL editor:
   1. Execute migrations/create_cases.sql
   2. Execute migrations/create_decision_metrics.sql
   ```

5. **Verify Setup**
   ```bash
   # Run the test suite
   pytest tests/ -v
   ```

## Development

### Running Tests
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_migrations.py

# Run with coverage
pytest --cov=src tests/
```

### Code Quality
The project uses several tools for code quality:
- `black` for code formatting
- `flake8` for style guide enforcement
- `mypy` for type checking
- `pylint` for code analysis

## Environment Variables

Required environment variables:
- `OPENAI_API_KEY`: API key for OpenAI GPT model access
- `SUPABASE_URL`: URL for your Supabase project
- `SUPABASE_KEY`: API key for Supabase access
- `SLACK_BOT_TOKEN`: Token for Slack notifications (if enabled)
- `EXECUTION_TIME_THRESHOLD`: Maximum execution time for agent tasks (default: 300)
- `SUCCESS_RATE_THRESHOLD`: Required success rate for agent operations (default: 0.95)
- `MAX_RETRIES`: Maximum number of retry attempts for failed operations (default: 3)
- `RETRY_DELAY`: Delay between retry attempts in seconds (default: 5)

## Error Handling

The system implements robust error handling with:
- Automatic retries for transient failures
- Structured logging for all operations
- Transaction support for database operations
- Graceful degradation when services are unavailable
- Detailed error reporting and notifications

## Performance Optimization

The system includes:
- Async patterns for improved throughput
- Connection pooling for database operations
- Caching for frequently accessed data
- Batch processing for bulk operations
- Performance metrics tracking and reporting

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run the test suite
5. Submit a pull request

## License

See the LICENSE file for details.
