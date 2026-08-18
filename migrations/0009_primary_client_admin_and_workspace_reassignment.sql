-- Migration 0009: Primary Client Admin Provisioning & Workspace Reassignment

DO $$
DECLARE
    client_admin_id INTEGER;
    dev_admin_id INTEGER;
    emp_user_id INTEGER;
BEGIN
    -- 1. Insert or update SKANOWAR (Primary Client Admin)
    IF NOT EXISTS (SELECT 1 FROM users WHERE LOWER(TRIM(username)) = 'skanowar') THEN
        INSERT INTO users (
            username, password_hash, full_name, qualifications, designation,
            license_no, expiry_date, membership_no, address_line_1, address_line_2,
            address_line_3, contact_no, email, role, admin_id, is_locked, must_change_password
        ) VALUES (
            'SKANOWAR',
            '$2b$12$o3M9qb4egOiJRl/DLsarSOqclTWz66prryXCp3fCraz3ism.Xjyf.',
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
    ELSE
        UPDATE users
        SET role = 'admin',
            full_name = 'SK ANOWAR ALI',
            qualifications = '(B.Tech (Automobile), LIIISLA)',
            designation = 'Surveyor & Loss Assessor',
            license_no = 'SLA-121784',
            expiry_date = '13-12-2026',
            membership_no = 'L/E/10721',
            address_line_1 = 'Natungram, P.O- Sondanga,',
            address_line_2 = 'P.S Nabadwip, City –Krishnanagar,',
            address_line_3 = 'Dist-Nadia, W.B.-741125',
            contact_no = '8777370714',
            email = 'skanowarali93@gmail.com',
            is_locked = FALSE
        WHERE LOWER(TRIM(username)) = 'skanowar'
        RETURNING id INTO client_admin_id;
    END IF;

    -- 2. Preserve NAMAN as Developer Admin
    UPDATE users
    SET role = 'admin',
        full_name = 'Naman Singh',
        designation = 'Developer & Administrator',
        email = 'naman@skinsurance.tech',
        is_locked = FALSE
    WHERE LOWER(TRIM(username)) = 'naman'
    RETURNING id INTO dev_admin_id;

    -- 3. Link USER employee account to SKANOWAR admin workspace
    SELECT id INTO emp_user_id FROM users WHERE LOWER(TRIM(username)) = 'user';
    IF emp_user_id IS NOT NULL AND client_admin_id IS NOT NULL THEN
        UPDATE users
        SET admin_id = client_admin_id,
            role = 'employee'
        WHERE id = emp_user_id;
    END IF;

    -- 4. Reassign workspace ownership of reports & fee bills to SKANOWAR
    IF client_admin_id IS NOT NULL THEN
        UPDATE reports
        SET workspace_admin_id = client_admin_id
        WHERE workspace_admin_id IS NULL OR workspace_admin_id = dev_admin_id OR user_id = emp_user_id;

        UPDATE fee_bills
        SET workspace_admin_id = client_admin_id
        WHERE workspace_admin_id IS NULL OR workspace_admin_id = dev_admin_id OR user_id = emp_user_id;
    END IF;
END $$;
