-- Migration 0008: Comprehensive Fee Bill Word Template, Report Linking & Photo Asset Scoping

ALTER TABLE fee_bills ADD COLUMN IF NOT EXISTS report_no VARCHAR(100);
ALTER TABLE fee_bills ADD COLUMN IF NOT EXISTS workspace_admin_id INTEGER REFERENCES users(id) ON DELETE CASCADE;
ALTER TABLE fee_bills ADD COLUMN IF NOT EXISTS date_of_accident VARCHAR(50);
ALTER TABLE fee_bills ADD COLUMN IF NOT EXISTS include_signature BOOLEAN DEFAULT true;
ALTER TABLE fee_bills ADD COLUMN IF NOT EXISTS fee_items JSONB;

CREATE INDEX IF NOT EXISTS idx_fee_bills_report_no ON fee_bills(report_no);
CREATE INDEX IF NOT EXISTS idx_fee_bills_workspace_admin_id ON fee_bills(workspace_admin_id);
