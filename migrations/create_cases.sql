-- Create UUID extension if not exists
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Wrap all operations in a transaction
BEGIN;

-- Create cases table if it doesn't exist
CREATE TABLE IF NOT EXISTS cases (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    external_id TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    modified_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    name TEXT NOT NULL,
    status TEXT NOT NULL,
    severity TEXT NOT NULL,
    score INTEGER NOT NULL DEFAULT 0,
    size INTEGER NOT NULL DEFAULT 0,
    tenant_name TEXT NOT NULL,
    assignee TEXT,
    created_by TEXT NOT NULL,
    modified_by TEXT,
    closed INTEGER NOT NULL DEFAULT 0,
    acknowledged INTEGER NOT NULL DEFAULT 0,
    start_timestamp BIGINT NOT NULL,
    end_timestamp BIGINT NOT NULL
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
        WHERE table_name = 'cases' AND column_name = 'score'
    ) INTO column_exists;
    
    IF NOT column_exists THEN
        ALTER TABLE cases ADD COLUMN score INTEGER NOT NULL DEFAULT 0;
    END IF;
    
    SELECT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'cases' AND column_name = 'size'
    ) INTO column_exists;
    
    IF NOT column_exists THEN
        ALTER TABLE cases ADD COLUMN size INTEGER NOT NULL DEFAULT 0;
    END IF;
    
    SELECT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'cases' AND column_name = 'tenant_name'
    ) INTO column_exists;
    
    IF NOT column_exists THEN
        ALTER TABLE cases ADD COLUMN tenant_name TEXT NOT NULL DEFAULT '';
    END IF;
    
    SELECT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'cases' AND column_name = 'closed'
    ) INTO column_exists;
    
    IF NOT column_exists THEN
        ALTER TABLE cases ADD COLUMN closed INTEGER NOT NULL DEFAULT 0;
    END IF;
    
    SELECT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'cases' AND column_name = 'acknowledged'
    ) INTO column_exists;
    
    IF NOT column_exists THEN
        ALTER TABLE cases ADD COLUMN acknowledged INTEGER NOT NULL DEFAULT 0;
    END IF;
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'Error adding columns: %', SQLERRM;
        RAISE;
END $$;

-- Create indexes if they don't exist
CREATE INDEX IF NOT EXISTS cases_external_id_idx ON cases(external_id);
CREATE INDEX IF NOT EXISTS cases_created_at_idx ON cases(created_at);
CREATE INDEX IF NOT EXISTS cases_modified_at_idx ON cases(modified_at);
CREATE INDEX IF NOT EXISTS cases_status_idx ON cases(status);
CREATE INDEX IF NOT EXISTS cases_severity_idx ON cases(severity);
CREATE INDEX IF NOT EXISTS cases_tenant_name_idx ON cases(tenant_name);

COMMIT;
