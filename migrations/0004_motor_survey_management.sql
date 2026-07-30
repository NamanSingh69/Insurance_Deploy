-- Motor Survey Management System: workspace ownership, RBAC, Gmail audit, and fee register fields.

ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(50) NOT NULL DEFAULT 'employee';
ALTER TABLE users ADD COLUMN IF NOT EXISTS admin_id INTEGER REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_locked BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS permissions JSONB NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE users ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE reports ADD COLUMN IF NOT EXISTS workspace_admin_id INTEGER REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE reports ADD COLUMN IF NOT EXISTS status VARCHAR(50) NOT NULL DEFAULT 'new_appointment';
ALTER TABLE reports ADD COLUMN IF NOT EXISTS survey_type VARCHAR(50) NOT NULL DEFAULT 'final';
ALTER TABLE reports ADD COLUMN IF NOT EXISTS gmail_message_id VARCHAR(255);
ALTER TABLE reports ADD COLUMN IF NOT EXISTS email_received_date TIMESTAMP;
ALTER TABLE reports ADD COLUMN IF NOT EXISTS updated_by INTEGER REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE reports ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE fee_bills ADD COLUMN IF NOT EXISTS workspace_admin_id INTEGER REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE fee_bills ADD COLUMN IF NOT EXISTS report_id VARCHAR(255) REFERENCES reports(id) ON DELETE SET NULL;
ALTER TABLE fee_bills ADD COLUMN IF NOT EXISTS professional_fee NUMERIC(12, 2) DEFAULT 0;
ALTER TABLE fee_bills ADD COLUMN IF NOT EXISTS gross_invoice_value NUMERIC(12, 2) DEFAULT 0;
ALTER TABLE fee_bills ADD COLUMN IF NOT EXISTS tds_amount NUMERIC(12, 2) DEFAULT 0;
ALTER TABLE fee_bills ADD COLUMN IF NOT EXISTS amount_received NUMERIC(12, 2) DEFAULT 0;
ALTER TABLE fee_bills ADD COLUMN IF NOT EXISTS outstanding_amount NUMERIC(12, 2) DEFAULT 0;
ALTER TABLE fee_bills ADD COLUMN IF NOT EXISTS due_date DATE;
ALTER TABLE fee_bills ADD COLUMN IF NOT EXISTS payment_status VARCHAR(50) NOT NULL DEFAULT 'unpaid';
ALTER TABLE fee_bills ADD COLUMN IF NOT EXISTS invoice_status VARCHAR(50) NOT NULL DEFAULT 'draft';
ALTER TABLE fee_bills ADD COLUMN IF NOT EXISTS fee_updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;

-- Preserve historical data; only copied values are used as initial values for the new fields.
UPDATE fee_bills
SET professional_fee = COALESCE(NULLIF(professional_fee, 0), taxable_amount, 0),
    gross_invoice_value = COALESCE(NULLIF(gross_invoice_value, 0), total_amount, 0)
WHERE professional_fee = 0 OR gross_invoice_value = 0;

CREATE TABLE IF NOT EXISTS gmail_integrations (
    workspace_admin_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    encrypted_token TEXT NOT NULL,
    mailbox_email VARCHAR(255),
    connected_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS gmail_sync_messages (
    gmail_message_id VARCHAR(255) PRIMARY KEY,
    workspace_admin_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    report_id VARCHAR(255) REFERENCES reports(id) ON DELETE SET NULL,
    sender_email VARCHAR(255),
    subject TEXT,
    received_at TIMESTAMP,
    parse_data_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    sync_status VARCHAR(50) NOT NULL DEFAULT 'processed',
    error_message TEXT,
    processed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS gmail_sender_domains (
    id SERIAL PRIMARY KEY,
    workspace_admin_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    domain VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (workspace_admin_id, domain)
);

CREATE INDEX IF NOT EXISTS reports_workspace_status_saved_idx
    ON reports (workspace_admin_id, status, saved_at DESC);
CREATE INDEX IF NOT EXISTS reports_workspace_claim_idx
    ON reports (workspace_admin_id, claim_no);
CREATE INDEX IF NOT EXISTS fee_bills_workspace_invoice_idx
    ON fee_bills (workspace_admin_id, invoice_date);
CREATE INDEX IF NOT EXISTS gmail_sync_workspace_processed_idx
    ON gmail_sync_messages (workspace_admin_id, processed_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS fee_bills_one_report_idx
    ON fee_bills (report_id) WHERE report_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS reports_workspace_report_no_idx
    ON reports (workspace_admin_id, report_no)
    WHERE workspace_admin_id IS NOT NULL AND report_no IS NOT NULL AND report_no <> '';

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'users_role_valid') THEN
        ALTER TABLE users ADD CONSTRAINT users_role_valid CHECK (role IN ('admin', 'employee'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'reports_status_valid') THEN
        ALTER TABLE reports ADD CONSTRAINT reports_status_valid CHECK (status IN (
            'new_appointment', 'inspection_pending', 'documents_awaited',
            'report_under_preparation', 'report_submitted', 'closed'
        ));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'reports_survey_type_valid') THEN
        ALTER TABLE reports ADD CONSTRAINT reports_survey_type_valid CHECK (survey_type IN ('spot', 'final'));
    END IF;
END $$;
