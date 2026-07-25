-- 0002_deduplicate_and_unique.sql
-- 1. Assign fallback number to reports with null or empty report_no
UPDATE reports
SET report_no = 'NO-NUMBER-' || id
WHERE report_no IS NULL OR report_no = '';

-- 2. Deduplicate (user_id, report_no) pairs by appending a sequential suffix to duplicates
WITH duplicate_reports AS (
    SELECT id, ROW_NUMBER() OVER(PARTITION BY user_id, report_no ORDER BY saved_at) as rn
    FROM reports
)
UPDATE reports
SET report_no = reports.report_no || '-dup' || (duplicate_reports.rn - 1)
FROM duplicate_reports
WHERE reports.id = duplicate_reports.id AND duplicate_reports.rn > 1;

-- 3. Add the unique constraint safely
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'reports_user_id_report_no_key'
    ) THEN
        ALTER TABLE reports ADD CONSTRAINT reports_user_id_report_no_key UNIQUE (user_id, report_no);
    END IF;
END $$;

