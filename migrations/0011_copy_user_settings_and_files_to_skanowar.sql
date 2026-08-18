-- Migration 0011: Copy user settings, files, signature, and workspace data from USER to SKANOWAR

DO $$
DECLARE
    client_admin_id INTEGER;
    dev_admin_id INTEGER;
    emp_user_id INTEGER;
BEGIN
    SELECT id INTO client_admin_id FROM users WHERE LOWER(TRIM(username)) = 'skanowar';
    SELECT id INTO dev_admin_id FROM users WHERE LOWER(TRIM(username)) = 'naman';
    SELECT id INTO emp_user_id FROM users WHERE LOWER(TRIM(username)) = 'user';

    -- 1. Ensure SKANOWAR user exists with admin role
    IF client_admin_id IS NULL THEN
        INSERT INTO users (
            username, password_hash, full_name, qualifications, designation,
            license_no, expiry_date, membership_no, address_line_1, address_line_2,
            address_line_3, contact_no, email, role, admin_id, is_locked, must_change_password
        ) VALUES (
            'SKANOWAR',
            '$2b$12$8Airc4KcKtll/a.ySWe2n.TEH.k3AdLm4P0bWkCIQ2TDH1dYDNmeu',
            'SK ANOWAR ALI',
            '(B.Tech (Automobile), LIIISLA)',
            'Surveyor & Loss Assessor',
            'SLA-121784',
            '13-12-2026',
            'L/E/10721',
            'Natungram, P.O- Sondanga,',
            'P.S Nabadwip, City –Krishnanagar,',
            'Dist-Nadia, W.B.-741125',
            '8777370714',
            'skanowarali93@gmail.com',
            'admin',
            NULL,
            FALSE,
            FALSE
        ) RETURNING id INTO client_admin_id;
    END IF;

    -- 2. Copy profile settings, API keys, signature, and metadata from USER to SKANOWAR
    IF emp_user_id IS NOT NULL AND client_admin_id IS NOT NULL THEN
        UPDATE users sk
        SET
            full_name = COALESCE(NULLIF(u.full_name, ''), sk.full_name, 'SK ANOWAR ALI'),
            qualifications = COALESCE(NULLIF(u.qualifications, ''), sk.qualifications, '(B.Tech (Automobile), LIIISLA)'),
            designation = COALESCE(NULLIF(u.designation, ''), sk.designation, 'Surveyor & Loss Assessor'),
            license_no = COALESCE(NULLIF(u.license_no, ''), sk.license_no, 'SLA-121784'),
            expiry_date = COALESCE(NULLIF(u.expiry_date, ''), sk.expiry_date, '13-12-2026'),
            membership_no = COALESCE(NULLIF(u.membership_no, ''), sk.membership_no, 'L/E/10721'),
            address_line_1 = COALESCE(NULLIF(u.address_line_1, ''), sk.address_line_1, 'Natungram, P.O- Sondanga,'),
            address_line_2 = COALESCE(NULLIF(u.address_line_2, ''), sk.address_line_2, 'P.S Nabadwip, City –Krishnanagar,'),
            address_line_3 = COALESCE(NULLIF(u.address_line_3, ''), sk.address_line_3, 'Dist-Nadia, W.B.-741125'),
            contact_no = COALESCE(NULLIF(u.contact_no, ''), sk.contact_no, '8777370714'),
            email = COALESCE(NULLIF(u.email, ''), sk.email, 'skanowarali93@gmail.com'),
            gemini_api_key = COALESCE(u.gemini_api_key, sk.gemini_api_key),
            gemini_model = COALESCE(u.gemini_model, sk.gemini_model),
            encrypted_gemini_api_key = COALESCE(u.encrypted_gemini_api_key, sk.encrypted_gemini_api_key),
            signature_asset_id = COALESCE(u.signature_asset_id, sk.signature_asset_id),
            permissions = COALESCE(u.permissions, sk.permissions, '{"gmail_sync": true}'::jsonb),
            role = 'admin',
            admin_id = NULL,
            is_locked = FALSE,
            must_change_password = FALSE
        FROM users u
        WHERE u.id = emp_user_id AND sk.id = client_admin_id;

        -- 3. Copy Google Drive integration from USER to SKANOWAR
        IF EXISTS (SELECT 1 FROM drive_integrations WHERE user_id = emp_user_id) THEN
            INSERT INTO drive_integrations (user_id, encrypted_token, account_email, connected_at, updated_at)
            SELECT client_admin_id, encrypted_token, account_email, connected_at, updated_at
            FROM drive_integrations WHERE user_id = emp_user_id
            ON CONFLICT (user_id) DO UPDATE
            SET encrypted_token = EXCLUDED.encrypted_token,
                account_email = EXCLUDED.account_email,
                updated_at = CURRENT_TIMESTAMP;
        END IF;

        -- 4. Reassign uploaded file assets (photos, signatures, documents) from USER to SKANOWAR
        UPDATE assets
        SET user_id = client_admin_id
        WHERE user_id = emp_user_id;

        -- 5. Copy report number counters so sequence continues
        INSERT INTO report_number_counters (user_id, prefix, report_year, next_sequence)
        SELECT client_admin_id, prefix, report_year, next_sequence
        FROM report_number_counters
        WHERE user_id = emp_user_id
        ON CONFLICT (user_id, prefix, report_year) DO UPDATE
        SET next_sequence = GREATEST(report_number_counters.next_sequence, EXCLUDED.next_sequence);

        -- 6. Link USER as employee under SKANOWAR
        UPDATE users
        SET role = 'employee',
            admin_id = client_admin_id,
            must_change_password = FALSE,
            is_locked = FALSE
        WHERE id = emp_user_id;
    END IF;

    -- 7. Ensure SKANOWAR is admin and not locked
    UPDATE users
    SET role = 'admin',
        admin_id = NULL,
        must_change_password = FALSE,
        is_locked = FALSE
    WHERE id = client_admin_id;

    -- 8. Reassign all reports and fee bills to SKANOWAR's workspace
    IF client_admin_id IS NOT NULL THEN
        UPDATE reports
        SET workspace_admin_id = client_admin_id
        WHERE workspace_admin_id IS NULL OR workspace_admin_id = dev_admin_id OR user_id = emp_user_id OR user_id = client_admin_id;

        UPDATE fee_bills
        SET workspace_admin_id = client_admin_id
        WHERE workspace_admin_id IS NULL OR workspace_admin_id = dev_admin_id OR user_id = emp_user_id OR user_id = client_admin_id;

        UPDATE insurer_master
        SET workspace_admin_id = client_admin_id
        WHERE workspace_admin_id IS NULL OR workspace_admin_id = dev_admin_id OR workspace_admin_id = emp_user_id;
    END IF;
END $$;
