-- Initial Schema Migration for IncidentMind CockroachDB
-- No real credentials or secrets are stored here.

-- 1. Create Users Table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    role VARCHAR(50) NOT NULL CHECK (role IN ('employee', 'admin')),
    department VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Create Incidents Table
CREATE TABLE IF NOT EXISTS incidents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    severity VARCHAR(50) NOT NULL CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    category VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'investigating', 'resolved', 'closed')),
    logs TEXT,
    embedding VECTOR(1024),
    reported_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Create Solution Attempts Table
CREATE TABLE IF NOT EXISTS solution_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_id UUID NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    solution_action TEXT NOT NULL,
    outcome VARCHAR(50) NOT NULL CHECK (outcome IN ('success', 'failure', 'partial', 'rejected', 'unknown')),
    notes TEXT,
    executed_by UUID REFERENCES users(id) ON DELETE SET NULL,
    execution_duration_ms INT,
    confidence_at_execution FLOAT,
    reward_delta INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Create Indexes for Optimization
CREATE INDEX IF NOT EXISTS idx_solution_attempts_incident_id ON solution_attempts (incident_id);
CREATE INDEX IF NOT EXISTS idx_solution_attempts_outcome ON solution_attempts (outcome);
CREATE INDEX IF NOT EXISTS idx_solution_attempts_created_at ON solution_attempts (created_at DESC);

-- 5. Create Vector Index for Similarity Searches
-- C-SPANN index to accelerate Euclidean distance queries (<->) on vector column
CREATE VECTOR INDEX IF NOT EXISTS idx_incidents_embedding ON incidents (embedding);
