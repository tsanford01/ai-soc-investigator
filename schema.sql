-- Cases table
create table cases (
    id uuid default uuid_generate_v4() primary key,
    external_id text unique not null,
    title text not null,
    severity text,
    status text,
    created_at timestamp with time zone default timezone('utc'::text, now()),
    modified_at timestamp with time zone default timezone('utc'::text, now()),
    summary jsonb,
    metadata jsonb
);

-- Alerts table
create table alerts (
    id uuid default uuid_generate_v4() primary key,
    case_id uuid references cases(id),
    external_id text,
    title text,
    severity text,
    created_at timestamp with time zone default timezone('utc'::text, now()),
    details jsonb
);

-- Observables table
create table observables (
    id uuid default uuid_generate_v4() primary key,
    alert_id uuid references alerts(id),
    type text,
    value text,
    created_at timestamp with time zone default timezone('utc'::text, now()),
    metadata jsonb
);

-- Analysis Results table
create table analysis_results (
    id uuid default uuid_generate_v4() primary key,
    case_id uuid references cases(id),
    severity_score float,
    priority_score float,
    key_indicators jsonb,
    patterns jsonb,
    created_at timestamp with time zone default timezone('utc'::text, now())
);

-- Action Items table
create table action_items (
    id uuid default uuid_generate_v4() primary key,
    case_id uuid references cases(id),
    action_type text,
    description text,
    priority text,
    status text default 'pending',
    created_at timestamp with time zone default timezone('utc'::text, now()),
    completed_at timestamp with time zone
);

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Workflows table
CREATE TABLE IF NOT EXISTS workflows (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    alert_id TEXT NOT NULL,
    status TEXT NOT NULL,
    current_stage TEXT NOT NULL,
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    stage_start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    error_message TEXT,
    metadata JSONB
);

-- Error logs table
CREATE TABLE IF NOT EXISTS error_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workflow_id UUID REFERENCES workflows(id),
    error_message TEXT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    metadata JSONB
);

-- Agent metrics table
CREATE TABLE IF NOT EXISTS agent_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_name TEXT NOT NULL,
    workflow_id UUID REFERENCES workflows(id),
    execution_time FLOAT NOT NULL,
    success BOOLEAN NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    metadata JSONB
);

-- Agent errors table
CREATE TABLE IF NOT EXISTS agent_errors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent TEXT NOT NULL,
    error TEXT NOT NULL,
    error_count INTEGER NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Workflow optimizations table
CREATE TABLE IF NOT EXISTS workflow_optimizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    bottlenecks JSONB NOT NULL,
    recommendations JSONB NOT NULL,
    performance_metrics JSONB NOT NULL
);

-- Stuck workflow analysis table
CREATE TABLE IF NOT EXISTS stuck_workflow_analysis (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workflow_id UUID REFERENCES workflows(id),
    stage TEXT NOT NULL,
    analysis JSONB NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS workflows_status_idx ON workflows(status);
CREATE INDEX IF NOT EXISTS workflows_current_stage_idx ON workflows(current_stage);
CREATE INDEX IF NOT EXISTS error_logs_workflow_id_idx ON error_logs(workflow_id);
CREATE INDEX IF NOT EXISTS agent_metrics_agent_name_idx ON agent_metrics(agent_name);
CREATE INDEX IF NOT EXISTS agent_metrics_workflow_id_idx ON agent_metrics(workflow_id);
CREATE INDEX IF NOT EXISTS idx_workflows_status ON workflows(status);
CREATE INDEX IF NOT EXISTS idx_workflows_current_stage ON workflows(current_stage);
CREATE INDEX IF NOT EXISTS idx_agent_metrics_name ON agent_metrics(agent_name);
CREATE INDEX IF NOT EXISTS idx_agent_errors_agent ON agent_errors(agent);
CREATE INDEX IF NOT EXISTS idx_stuck_workflow_workflow_id ON stuck_workflow_analysis(workflow_id);
