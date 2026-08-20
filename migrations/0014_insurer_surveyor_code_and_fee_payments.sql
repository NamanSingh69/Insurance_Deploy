-- Migration 0014: Insurer Master Surveyor Code and Fee Bill Payment Lifecycle Management
-- Client Change Request (2026-08-20)

-- 1. Add insurer-specific surveyor code to insurer_master
ALTER TABLE insurer_master ADD COLUMN IF NOT EXISTS surveyor_code VARCHAR(100);

-- 2. Ensure fee_bills has complete payment lifecycle columns
ALTER TABLE fee_bills ADD COLUMN IF NOT EXISTS payment_status VARCHAR(50) NOT NULL DEFAULT 'unpaid';
ALTER TABLE fee_bills ADD COLUMN IF NOT EXISTS payment_date DATE;
ALTER TABLE fee_bills ADD COLUMN IF NOT EXISTS payment_reference VARCHAR(100);
ALTER TABLE fee_bills ADD COLUMN IF NOT EXISTS payment_remarks TEXT;

-- 3. Create index for fast status and date queries
CREATE INDEX IF NOT EXISTS idx_fee_bills_payment_status ON fee_bills(workspace_admin_id, payment_status);
