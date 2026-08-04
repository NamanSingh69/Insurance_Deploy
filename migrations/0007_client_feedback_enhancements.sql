-- Migration 0007: Client Feedback Enhancements (Insurer Master, Conveyance Formula, Gmail Staging, Photo Tagging, Claim Contact Details)

-- 1. Insurer Master Table
CREATE TABLE IF NOT EXISTS insurer_master (
    id SERIAL PRIMARY KEY,
    workspace_admin_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    insurer_name VARCHAR(255) NOT NULL,
    branch_name VARCHAR(255),
    branch_address TEXT,
    gstin VARCHAR(50),
    state_code VARCHAR(10) DEFAULT '19',
    invoice_prefix VARCHAR(50) NOT NULL,
    default_conveyance_rate NUMERIC(10, 2) DEFAULT 10.00,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(workspace_admin_id, insurer_name, branch_name)
);

-- 2. Upgrades to reports (claims) table
ALTER TABLE reports ADD COLUMN IF NOT EXISTS insured_email VARCHAR(255);
ALTER TABLE reports ADD COLUMN IF NOT EXISTS claim_manager_email VARCHAR(255);
ALTER TABLE reports ADD COLUMN IF NOT EXISTS claim_manager_phone VARCHAR(50);
ALTER TABLE reports ADD COLUMN IF NOT EXISTS financial_year VARCHAR(50);
ALTER TABLE reports ADD COLUMN IF NOT EXISTS insurer_branch_id INTEGER REFERENCES insurer_master(id) ON DELETE SET NULL;
ALTER TABLE reports ADD COLUMN IF NOT EXISTS vehicle_type VARCHAR(100);
ALTER TABLE reports ADD COLUMN IF NOT EXISTS pending_documents_notes TEXT;
ALTER TABLE reports ADD COLUMN IF NOT EXISTS psr_status VARCHAR(50) DEFAULT 'pending';
ALTER TABLE reports ADD COLUMN IF NOT EXISTS final_report_status VARCHAR(50) DEFAULT 'pending';

-- 3. Upgrades to fee_bills table
ALTER TABLE fee_bills ADD COLUMN IF NOT EXISTS conveyance_mode VARCHAR(50) DEFAULT 'flat';
ALTER TABLE fee_bills ADD COLUMN IF NOT EXISTS distance_km NUMERIC(10, 2) DEFAULT 0;
ALTER TABLE fee_bills ADD COLUMN IF NOT EXISTS conveyance_rate_per_km NUMERIC(10, 2) DEFAULT 10.00;
ALTER TABLE fee_bills ADD COLUMN IF NOT EXISTS visit_count INTEGER DEFAULT 1;
ALTER TABLE fee_bills ADD COLUMN IF NOT EXISTS insurer_prefix VARCHAR(50);
ALTER TABLE fee_bills ADD COLUMN IF NOT EXISTS insurer_seq_num INTEGER DEFAULT 1;

-- 4. Upgrades to assets (claim photos)
ALTER TABLE assets ADD COLUMN IF NOT EXISTS category_tag VARCHAR(50) DEFAULT 'Final';

-- 5. Gmail Intimations Staging Table
CREATE TABLE IF NOT EXISTS gmail_intimations_staging (
    id SERIAL PRIMARY KEY,
    workspace_admin_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    gmail_message_id VARCHAR(255) NOT NULL,
    sender_email VARCHAR(255),
    subject TEXT,
    received_at TIMESTAMP,
    extracted_claim_no VARCHAR(255),
    extracted_insured_name VARCHAR(255),
    extracted_vehicle_no VARCHAR(255),
    extracted_policy_no VARCHAR(255),
    extracted_insurer_name VARCHAR(255),
    raw_body TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(workspace_admin_id, gmail_message_id)
);

CREATE INDEX IF NOT EXISTS idx_insurer_master_workspace ON insurer_master(workspace_admin_id);
CREATE INDEX IF NOT EXISTS idx_gmail_staging_workspace_status ON gmail_intimations_staging(workspace_admin_id, status);
