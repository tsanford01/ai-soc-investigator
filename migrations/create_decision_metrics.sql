-- Create UUID extension if not exists
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Wrap all operations in a transaction
BEGIN;

-- Create decision metrics table if it doesn't exist
CREATE TABLE IF NOT EXISTS decision_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    decision_type TEXT NOT NULL,
    decision_value JSONB NOT NULL,
    confidence FLOAT NOT NULL DEFAULT 0.0,
    risk_level TEXT,
    priority INTEGER,
    needs_investigation BOOLEAN DEFAULT false,
    automated_actions JSONB,
    required_human_actions JSONB,
    model TEXT NOT NULL,
    prompt TEXT NOT NULL,
    completion TEXT NOT NULL
);

-- Add columns if they don't exist (safe to run multiple times)
DO $$ 
DECLARE
    column_exists boolean;
BEGIN
    -- Add new columns if they don't exist
    SELECT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'decision_metrics' AND column_name = 'risk_level'
    ) INTO column_exists;
    
    IF NOT column_exists THEN
        ALTER TABLE decision_metrics ADD COLUMN risk_level TEXT;
    END IF;
    
    SELECT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'decision_metrics' AND column_name = 'priority'
    ) INTO column_exists;
    
    IF NOT column_exists THEN
        ALTER TABLE decision_metrics ADD COLUMN priority INTEGER;
    END IF;
    
    SELECT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'decision_metrics' AND column_name = 'needs_investigation'
    ) INTO column_exists;
    
    IF NOT column_exists THEN
        ALTER TABLE decision_metrics ADD COLUMN needs_investigation BOOLEAN DEFAULT false;
    END IF;
    
    SELECT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'decision_metrics' AND column_name = 'automated_actions'
    ) INTO column_exists;
    
    IF NOT column_exists THEN
        ALTER TABLE decision_metrics ADD COLUMN automated_actions JSONB;
    END IF;
    
    SELECT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'decision_metrics' AND column_name = 'required_human_actions'
    ) INTO column_exists;
    
    IF NOT column_exists THEN
        ALTER TABLE decision_metrics ADD COLUMN required_human_actions JSONB;
    END IF;
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'Error adding columns: %', SQLERRM;
        RAISE;
END $$;

-- Create indexes if they don't exist
CREATE INDEX IF NOT EXISTS decision_metrics_case_id_idx ON decision_metrics(case_id);
CREATE INDEX IF NOT EXISTS decision_metrics_created_at_idx ON decision_metrics(created_at);
CREATE INDEX IF NOT EXISTS decision_metrics_decision_type_idx ON decision_metrics(decision_type);
CREATE INDEX IF NOT EXISTS decision_metrics_risk_level_idx ON decision_metrics(risk_level);
CREATE INDEX IF NOT EXISTS decision_metrics_priority_idx ON decision_metrics(priority);
CREATE INDEX IF NOT EXISTS decision_metrics_needs_investigation_idx ON decision_metrics(needs_investigation);

COMMIT;
