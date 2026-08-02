-- Migration 0005: Fee bill convenience & photocopy fields, Gmail cancellation, and document pending reminders

ALTER TABLE fee_bills ADD COLUMN IF NOT EXISTS convenience_route VARCHAR(255);
ALTER TABLE fee_bills ADD COLUMN IF NOT EXISTS convenience_km NUMERIC(10, 2) DEFAULT 0;
ALTER TABLE fee_bills ADD COLUMN IF NOT EXISTS convenience_rate NUMERIC(10, 2) DEFAULT 0;
ALTER TABLE fee_bills ADD COLUMN IF NOT EXISTS conveyance_fee NUMERIC(12, 2) DEFAULT 0;
ALTER TABLE fee_bills ADD COLUMN IF NOT EXISTS photocopy_amount NUMERIC(12, 2) DEFAULT 0;

ALTER TABLE gmail_sync_messages ADD COLUMN IF NOT EXISTS sync_status VARCHAR(50) DEFAULT 'processed';

CREATE TABLE IF NOT EXISTS claim_reminders (
    id SERIAL PRIMARY KEY,
    workspace_admin_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    report_id VARCHAR(255) UNIQUE REFERENCES reports(id) ON DELETE CASCADE,
    claim_no VARCHAR(255),
    reminder_count INTEGER NOT NULL DEFAULT 0,
    last_sent_at TIMESTAMP,
    next_due_at TIMESTAMP,
    claim_manager_email VARCHAR(255),
    claim_manager_phone VARCHAR(50),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_claim_reminders_report ON claim_reminders(report_id);
