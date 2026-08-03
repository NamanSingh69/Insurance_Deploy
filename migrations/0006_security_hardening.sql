-- Security hardening: encrypted credentials, private-file metadata, and Drive ownership.

ALTER TABLE users ADD COLUMN IF NOT EXISTS encrypted_gemini_api_key TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS signature_asset_id VARCHAR(255)
    REFERENCES assets(id) ON DELETE SET NULL;

CREATE TABLE IF NOT EXISTS drive_integrations (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    encrypted_token TEXT NOT NULL,
    account_email VARCHAR(255),
    connected_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE assets ADD COLUMN IF NOT EXISTS purpose VARCHAR(32) NOT NULL DEFAULT 'generic';
ALTER TABLE assets ADD COLUMN IF NOT EXISTS size_bytes BIGINT;
ALTER TABLE assets ADD COLUMN IF NOT EXISTS checksum_sha256 CHAR(64);

CREATE INDEX IF NOT EXISTS assets_report_id_idx ON assets (report_id);
CREATE INDEX IF NOT EXISTS assets_expiry_idx ON assets (expires_at) WHERE expires_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS drive_integrations_updated_at_idx ON drive_integrations (updated_at);
