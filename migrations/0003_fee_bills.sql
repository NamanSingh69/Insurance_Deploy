CREATE TABLE IF NOT EXISTS fee_bills (
    id VARCHAR(255) PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    invoice_no VARCHAR(100) NOT NULL,
    invoice_date VARCHAR(50) NOT NULL,
    insurer_name VARCHAR(255) NOT NULL,
    insured_name VARCHAR(255) NOT NULL,
    policy_no VARCHAR(100),
    claim_no VARCHAR(100),
    vehicle_no VARCHAR(100),
    taxable_amount NUMERIC(12, 2) DEFAULT 0,
    gst_pc NUMERIC(5, 2) DEFAULT 18,
    gst_amount NUMERIC(12, 2) DEFAULT 0,
    total_amount NUMERIC(12, 2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    bill_data_json JSONB
);

CREATE INDEX IF NOT EXISTS idx_fee_bills_user_id ON fee_bills(user_id);
CREATE INDEX IF NOT EXISTS idx_fee_bills_created_at ON fee_bills(created_at);
