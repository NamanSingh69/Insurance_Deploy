-- 0002_deduplicate_and_unique.sql
-- Deduplicate (user_id, report_no) pairs by appending a sequential suffix to the duplicates
WITH duplicate_reports AS (
    SELECT id, ROW_NUMBER() OVER(PARTITION BY user_id, report_no ORDER BY saved_at) as rn
    FROM reports
    WHERE report_no IS NOT NULL AND report_no != ''
)
UPDATE reports
SET report_no = reports.report_no || '-dup' || (duplicate_reports.rn - 1)
FROM duplicate_reports
WHERE reports.id = duplicate_reports.id AND duplicate_reports.rn > 1;

-- Add the unique constraint to enforce uniqueness of report_no per user
ALTER TABLE reports ADD CONSTRAINT reports_user_id_report_no_key UNIQUE (user_id, report_no);
