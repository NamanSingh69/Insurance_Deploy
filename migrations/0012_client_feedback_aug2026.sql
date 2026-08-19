-- Migration 0012: Client Feedback August 2026 (User Segregation, Multi-Branch Insurer Masters, Robust Fee Bills)

-- 1. Ensure indexes on fee_bills and reports for user and workspace scoping
CREATE INDEX IF NOT EXISTS idx_fee_bills_workspace_admin ON fee_bills(workspace_admin_id);
CREATE INDEX IF NOT EXISTS idx_fee_bills_user_id ON fee_bills(user_id);
CREATE INDEX IF NOT EXISTS idx_reports_workspace_user ON reports(workspace_admin_id, user_id);
CREATE INDEX IF NOT EXISTS idx_insurer_master_name ON insurer_master(workspace_admin_id, insurer_name);

-- 2. Ensure created_by / updated_by consistency on reports
ALTER TABLE reports ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id);
ALTER TABLE reports ADD COLUMN IF NOT EXISTS created_by INTEGER REFERENCES users(id);
ALTER TABLE reports ADD COLUMN IF NOT EXISTS updated_by INTEGER REFERENCES users(id);
