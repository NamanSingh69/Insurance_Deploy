-- Migration 0012: Multi-tenant database isolation, Pranay Maity Admin, and USER1 Employee provisioning

DO $$
DECLARE
    skanowar_id INTEGER;
    pranay_id INTEGER;
    dev_id INTEGER;
    user_emp_id INTEGER;
    user1_emp_id INTEGER;
BEGIN
    -- 1. Get or create SKANOWAR Admin
    SELECT id INTO skanowar_id FROM users WHERE LOWER(TRIM(username)) = 'skanowar';
    IF skanowar_id IS NOT NULL THEN
        UPDATE users SET
            role = 'admin',
            admin_id = NULL,
            is_locked = FALSE,
            must_change_password = FALSE
        WHERE id = skanowar_id;
    END IF;

    -- 2. Get or create PRANAYMAITY Admin
    SELECT id INTO pranay_id FROM users WHERE LOWER(TRIM(username)) IN ('pranaymaity', 'pranay');
    IF pranay_id IS NULL THEN
        INSERT INTO users (
            username, password_hash, full_name, qualifications, designation,
            license_no, expiry_date, membership_no, address_line_1, address_line_2,
            address_line_3, contact_no, email, role, admin_id, is_locked, must_change_password
        ) VALUES (
            'PRANAYMAITY',
            '$2b$12$8Airc4KcKtll/a.ySWe2n.TEH.k3AdLm4P0bWkCIQ2TDH1dYDNmeu',
            'Pranay Maity',
            '(B.Tech, Surveyor)',
            'Surveyor & Loss Assessor',
            'SLA-PRANAY',
            '31-12-2027',
            'L/E/PRANAY',
            'Kolkata, West Bengal',
            '',
            '',
            '9876543210',
            'pranaymaity@gmail.com',
            'admin',
            NULL,
            FALSE,
            FALSE
        ) RETURNING id INTO pranay_id;
    ELSE
        UPDATE users SET
            role = 'admin',
            admin_id = NULL,
            full_name = COALESCE(NULLIF(full_name, ''), 'Pranay Maity'),
            is_locked = FALSE,
            must_change_password = FALSE
        WHERE id = pranay_id;
    END IF;

    -- 3. Get or create NAMAN Developer Admin
    SELECT id INTO dev_id FROM users WHERE LOWER(TRIM(username)) = 'naman';
    IF dev_id IS NOT NULL THEN
        UPDATE users SET role = 'admin', admin_id = NULL WHERE id = dev_id;
    END IF;

    -- 4. Get or create USER (Employee under SKANOWAR)
    SELECT id INTO user_emp_id FROM users WHERE LOWER(TRIM(username)) = 'user';
    IF user_emp_id IS NOT NULL AND skanowar_id IS NOT NULL THEN
        UPDATE users SET
            role = 'employee',
            admin_id = skanowar_id,
            is_locked = FALSE,
            must_change_password = FALSE
        WHERE id = user_emp_id;
    END IF;

    -- 5. Get or create USER1 (Employee under PRANAYMAITY)
    SELECT id INTO user1_emp_id FROM users WHERE LOWER(TRIM(username)) = 'user1';
    IF user1_emp_id IS NULL THEN
        INSERT INTO users (
            username, password_hash, full_name, role, admin_id, is_locked, must_change_password
        ) VALUES (
            'USER1',
            '$2b$12$8Airc4KcKtll/a.ySWe2n.TEH.k3AdLm4P0bWkCIQ2TDH1dYDNmeu',
            'USER1 (Assistant)',
            'employee',
            pranay_id,
            FALSE,
            FALSE
        ) RETURNING id INTO user1_emp_id;
    ELSE
        UPDATE users SET
            role = 'employee',
            admin_id = pranay_id,
            is_locked = FALSE,
            must_change_password = FALSE
        WHERE id = user1_emp_id;
    END IF;

    -- 6. Ensure SKANOWAR's workspace owns his reports and fee bills
    IF skanowar_id IS NOT NULL THEN
        UPDATE reports
        SET workspace_admin_id = skanowar_id
        WHERE workspace_admin_id IS NULL OR user_id = user_emp_id OR user_id = skanowar_id;

        UPDATE fee_bills
        SET workspace_admin_id = skanowar_id
        WHERE workspace_admin_id IS NULL OR user_id = user_emp_id OR user_id = skanowar_id;

        UPDATE insurer_master
        SET workspace_admin_id = skanowar_id
        WHERE workspace_admin_id IS NULL OR workspace_admin_id = user_emp_id;
    END IF;

    -- 7. Ensure USER1 files (if any exist) are assigned to PRANAYMAITY workspace
    IF pranay_id IS NOT NULL AND user1_emp_id IS NOT NULL THEN
        UPDATE reports
        SET workspace_admin_id = pranay_id
        WHERE user_id = user1_emp_id;

        UPDATE fee_bills
        SET workspace_admin_id = pranay_id
        WHERE user_id = user1_emp_id;
    END IF;
END $$;
