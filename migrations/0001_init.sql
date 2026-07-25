-- 0001_init.sql
-- Create Users Table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    qualifications VARCHAR(255),
    designation VARCHAR(255),
    license_no VARCHAR(255),
    expiry_date VARCHAR(255),
    membership_no VARCHAR(255),
    address_line_1 VARCHAR(255),
    address_line_2 VARCHAR(255),
    address_line_3 VARCHAR(255),
    contact_no VARCHAR(255),
    email VARCHAR(255),
    gemini_api_key VARCHAR(255),
    gemini_model VARCHAR(255)
);

-- Create Reports Table
CREATE TABLE IF NOT EXISTS reports (
    id VARCHAR(255) PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    report_no TEXT,
    insured_name TEXT,
    vehicle_no TEXT,
    claim_no TEXT,
    policy_no TEXT,
    saved_at TIMESTAMP,
    include_in_consolidated BOOLEAN DEFAULT TRUE,
    report_data_json JSONB
);

-- Durable ownership records for every file the application serves.
CREATE TABLE IF NOT EXISTS assets (
    id VARCHAR(255) PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    storage_kind VARCHAR(32) NOT NULL,
    storage_locator TEXT NOT NULL,
    filename TEXT,
    mime_type VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    report_id VARCHAR(255) REFERENCES reports(id) ON DELETE SET NULL
);

-- Jobs live in PostgreSQL
CREATE TABLE IF NOT EXISTS jobs (
    id VARCHAR(255) PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kind VARCHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL,
    input_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    result_json JSONB,
    error_message TEXT,
    attempts INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    locked_at TIMESTAMP,
    worker_id VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS upload_sessions (
    id VARCHAR(255) PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider VARCHAR(32) NOT NULL,
    filename TEXT NOT NULL,
    mime_type VARCHAR(255) NOT NULL,
    expected_size BIGINT NOT NULL,
    provider_uri TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL
);

-- Counters for atomic report number generation
CREATE TABLE IF NOT EXISTS report_number_counters (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    prefix VARCHAR(16) NOT NULL,
    report_year VARCHAR(4) NOT NULL,
    next_sequence INTEGER NOT NULL,
    PRIMARY KEY (user_id, prefix, report_year)
);

CREATE INDEX IF NOT EXISTS reports_user_saved_at_idx ON reports (user_id, saved_at DESC);
CREATE INDEX IF NOT EXISTS assets_user_id_idx ON assets (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS jobs_status_created_at_idx ON jobs (status, created_at);
