# Motor Survey Report Generator — Operations Context

## Overview

This Flask application manages motor-survey reports, a shared Claim Register, fee records, Google Drive uploads, and Gemini-assisted document and Gmail claim extraction.  Production is served by Gunicorn behind Nginx at `https://skinsurance.tech` with PostgreSQL as the application database.

## Security and configuration

Keep all credentials in the protected production environment file, never in Git, scripts, screenshots, tickets, or this document.  Any credential previously committed or shared in repository documentation must be rotated before production use.

The production environment requires at least:

```text
DATABASE_URL=
FLASK_SECRET_KEY=
GEMINI_API_KEY=
GOOGLE_SHEETS_CREDENTIALS=
GOOGLE_DRIVE_FOLDER_ID=
GMAIL_TOKEN_ENCRYPTION_KEY=
GMAIL_OAUTH_CLIENT_ID=
GMAIL_OAUTH_CLIENT_SECRET=
GMAIL_OAUTH_REDIRECT_URI=https://skinsurance.tech/auth/gmail/callback
```

`GMAIL_TOKEN_ENCRYPTION_KEY` must be a Fernet key generated outside source control.  Gmail OAuth requires a redirect URI matching the deployed domain and must request only `gmail.readonly` for mailbox sync.  Gmail source messages are intentionally not modified.

## Workspace model

- Existing reports and fee bills without a workspace remain private to their legacy owner.
- New operational records are scoped to an admin workspace.
- Admins can manage users, finance, exports, invoice numbers, Gmail connections, and sender domains.
- Employees can work on shared claims and reports. Financial data is redacted from their API responses and cannot be overwritten by their saves.
- Locked users cannot sign in or continue an existing session.

After deploying the workspace migration, promote the intended existing owner before inviting employees:

```bash
cd /var/www/insurance-app
sudo venv/bin/flask promote-admin <username>
sudo venv/bin/flask create-employee <username> <temporary-password> --admin <admin-username>
```

Use `--gmail-sync` only for employees who are explicitly permitted to start a mailbox sync.

## Deployment

From the local checkout:

```bash
git pull --ff-only
git push origin main
```

On the VPS:

```bash
cd /var/www/insurance-app
git pull --ff-only origin main
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart insurance
sudo systemctl reload nginx
```

Database migrations run safely at application startup. Verify the service and the migration state after every deployment:

```bash
systemctl is-active insurance
systemctl is-active nginx
export PGPASSWORD='<read from the protected production environment>'
./vps_setup/verify_deployment.sh
```

Then verify the public login page:

```bash
curl -fsS -o /dev/null -w '%{http_code}\n' https://skinsurance.tech/login
```

## Backup and recovery

Create backups outside the web root and protect them with filesystem permissions. Do not publish a database dump under `/static` or any public path. Test restores in a non-production database before using them for recovery.

## Key application locations

- Application: `/var/www/insurance-app`
- Systemd unit: `/etc/systemd/system/insurance.service`
- Nginx site: `/etc/nginx/sites-available/skinsurance`
- Production environment file: `/var/www/insurance-app/.env` (mode `600`, outside source control)

## System Credentials & VPS Operations Reference

### VPS Host Credentials
- **Host IP:** `185.199.52.85`
- **IPv6:** `2a02:4780:12:aa78::1`
- **Username:** `root`
- **Password:** `surveyorportal@2026`
- **SSH Port:** `22`
- **Hostinger VPS ID:** `1789781`
- **Hostinger Firewall ID:** `319602`

### Database Details
- **Engine:** PostgreSQL (local instance on port 5432)
- **Database Name:** `insurance_db`
- **DB User:** `insurance_user`
- **DB Password:** `surveyorportal@2026`
- **Connection String:** `postgresql://insurance_user:surveyorportal@2026@localhost/insurance_db`

### Default Application Login Credentials
- **Admin User:** `NAMAN` / `69420`
- **Employee User:** `USER` / `UH65A#DF`

## Architecture & Feature Decisions

- **Survey Fee PDF Extraction**: Uploaded policy or RC PDFs extract key fields (Insurer, Insured, Vehicle No, Policy No) directly into the live Survey Fee Register form fields for visual review, allowing the user to enter professional fees manually before saving.
- **Dashboard Drill-down**: Clicking any dashboard metric card switches to the Claim Register tab with status filters pre-applied. Clicking "Documents Awaited" opens a dedicated missing-documents checklist modal for granular document tracking.
- **Dashboard Date Range Filter**: A quick-select dropdown ('1 Month' default, '3 Months', '1 Year', 'All Time') dynamically updates all operational and financial metrics.
- **Consolidated CSV Export**: Includes 'Insurer Company Name' (positioned next to Insured Name) and 'Assigned Date' (positioned next to Invoice Date).
- **Automated Daily Backup**: Background daily backup to Google Drive with an Admin Settings button to download backup snapshots on demand.