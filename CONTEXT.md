# Motor Survey Report Generator — Complete Architecture & Operations Context

**Production Domain:** [https://skinsurance.tech](https://skinsurance.tech)  
**Target User / Surveyor:** Sk Anowar Ali  
**Core Framework:** Python 3.12+, Flask 3.1, Gunicorn 23.0 (`--workers 3 --threads 4`), PostgreSQL 14+, Redis, Nginx Reverse Proxy (Let's Encrypt SSL).

---

## 1. System Credentials & VPS Operations Reference

### VPS Host Access
- **Host IP:** `185.199.52.85`
- **IPv6:** `2a02:4780:12:aa78::1`
- **SSH Port:** `22` (Enabled via Hostinger Firewall profile `vps-allow-all`)
- **Root User:** `root`
- **Root Password:** `surveyorportal@2026`
- **Hostinger VPS ID:** `1789781` | **Hostinger Firewall ID:** `319602`
- **Application Root:** `/var/www/insurance-app`
- **Virtual Environment:** `/var/www/insurance-app/venv` (or `.venv`)

### PostgreSQL Database
- **Engine:** PostgreSQL 14+ (Local instance on `localhost:5432`)
- **Database Name:** `insurance_db`
- **Database User:** `insurance_user`
- **Database Password:** `surveyorportal@2026`
- **Connection URI:** `postgresql://insurance_user:surveyorportal@2026@localhost/insurance_db`
- **Pre-Deploy Snapshot Backup:** `/root/backups/insurance_db_pre_deploy_20260815_183446.sql` (152 KB)

### Application Accounts & Roles
- **Primary Client Administrator Account:** `SKANOWAR` / `AnowarAdmin@2026` (ID: 3)
  - Primary account for surveyor Sk Anowar Ali.
  - Full client workspace ownership, all reports and claims visibility, financial Survey Fee Register, Insurer Master management, GSTR-1 / CA Excel tax exports, employee user management, and system settings.
- **Developer Administrator Account:** `NAMAN` / `69420` (ID: 2)
  - Dedicated developer account for system maintenance, enhancements, and diagnostic administration.
- **Employee Account:** `USER` / `UH65A#DF` (ID: 1, `admin_id`: 3)
  - Field staff and surveyor assistant account linked to `SKANOWAR`'s workspace.
  - Operational claim management, survey report creation/editing, photo uploads, fee bill drafting/PDF downloads.
  - **Restrictions:** Cannot delete reports (`403 Forbidden`), cannot delete fee bills (`403 Forbidden`), cannot view overall corporate financial dashboard totals or download GSTR-1/CA tax exports (`403 Forbidden`).

---

## 2. Automated CI/CD & Zero-Friction Deployment Pipeline

### How Deployment Works (Push-to-Deploy)
The deployment process is **100% automated**. Pushing code to `origin/main` automatically updates production in **~3.5 seconds** with zero manual server interaction:

```bash
git add -A
git commit -m "your commit message"
git push origin main
```

Or execute the local deployment script:
```bash
python scripts/deploy.py
```

### Webhook & Automation Architecture
- **GitHub Webhook ID:** `666295837` (`NamanSingh69/Insurance_Deploy`)
- **Webhook Endpoint:** `https://skinsurance.tech/api/deploy-webhook` (POST)
- **Signature Security:** HMAC SHA-256 validated via `X-Hub-Signature-256` header against `DEPLOY_WEBHOOK_SECRET` (`surveyorportal-deploy-2026`).
- **Server Deployment Script:** `/var/www/insurance-app/vps_setup/auto_deploy.sh`
  1. `git fetch origin main && git reset --hard origin/main`
  2. `pip install -r requirements.txt --quiet`
  3. `systemctl restart insurance.service insurance-worker.service nginx.service`
  4. Liveness validation against `http://127.0.0.1:5000/healthz` (HTTP 200 OK)
  5. Audit log recorded to `/var/log/insurance_deploy.log`.
- **Sudoers Permission Rule:** `/etc/sudoers.d/insurance_deploy` grants `www-data` passwordless execution of `systemctl restart/reload` for insurance services.

---

## 3. Dynamic Asset Cache-Busting

- **Context Processor:** In [app.py](file:///c:/Users/namsi/Desktop/Freelance/Insurance%20-%20SK/app.py), `inject_request_security_values` extracts the active Git commit hash (`git rev-parse --short HEAD`) and exposes it to Jinja templates as `app_version`.
- **Template Binding:** In [templates/index.html](file:///c:/Users/namsi/Desktop/Freelance/Insurance%20-%20SK/templates/index.html) and [templates/login.html](file:///c:/Users/namsi/Desktop/Freelance/Insurance%20-%20SK/templates/login.html):
  - Stylesheet: `{{ url_for('static', filename='style.css') }}?v={{ app_version }}`
  - Script: `{{ url_for('static', filename='script.js') }}?v={{ app_version }}`
- **Benefit:** Client browsers and Cloudflare/Nginx CDN caches immediately invalidate upon new commits, preventing stale JavaScript/CSS bugs.

---

## 4. Key Feature Implementations & Architecture Matrix

| Feature Area | Implementation Detail | Technical Seam |
|---|---|---|
| **R1: In-Place Dashboard Drilldown** | Clicking KPI cards (*Pending claims*, *Inspection pending*, *Documents awaited*, etc.) renders filtered claim lists directly below cards in `#dashboard-drilldown-section` without tab switching. Active card receives `.active-metric-card` highlight border. | `static/script.js` (`renderDashboardDrilldown`), `#dashboard-drilldown-section` |
| **R2: Missing Documents Checklist Modal** | Clicking `Docs` button in Claim Register opens `#pending-documents-modal` with granular item checklists, instant toggle updates, and automated reminder counter. Zero console errors. | `static/script.js` (`openPendingDocsModal`), `#pending-documents-modal` |
| **R3: Master Insurer Guidance & Setup** | Survey Fee Register includes guidance banner and `+ Manage Insurer Masters` quick action (`.open-insurer-master-modal-btn`) launching `#insurer-master-modal` to configure master insurer records (GSTIN, Address, Default Rate/Km, Prefix). | `static/script.js` (`loadInsurerMasters`), `#insurer-master-modal` |
| **R4: Smart Auto-Prefix & Sequential Invoicing** | Typing insurer name (e.g. *National Insurance Company*) auto-derives smart uppercase prefix (e.g. `NIC-0001`, `OGI-0001`), auto-fills GSTIN & address, and fetches next sequential invoice number from `/api/insurers/next-invoice-no`. | `static/script.js` (`deriveInsurerAcronym`, `handleFeeInsurerInput`), `/api/insurers/next-invoice-no` |
| **R5: Whole Rupee Stepper & Live Summary** | Professional fee input enforces integer step (`step="1"`). Live summary card (`#fee-live-calc-box`) dynamically recalculates: $\text{Taxable} = \text{Prof} + \text{Conv} + \text{Photo}$, $\text{GST (18\%)}$, $\text{Gross Total}$. | `static/script.js` (`updateLiveFeeSummary`), `#fee-live-calc-box` |
| **R6: Photo Upload Rate Limiting & Diagnostics** | HD damage photo uploader supports batch drag-and-drop with adaptive client throttling. Replaced false Google Drive quota alerts with accurate server error diagnostics. Rate limits: 300/hr, 60/min. | `static/script.js` (Upload dropzones), Flask-Limiter config |
| **Nil Depreciation & Towing Engine** | Policy types: *Comprehensive*, *Third Party*, *Nil Depreciation*, *Nil Depreciation Plus*. Nil Depreciation applies 0% depreciation on parts except statutory items (tyres/tubes/battery/rubber/glass). Towing charges calculated in summary & PDF. | [modules/pdf.py](file:///c:/Users/namsi/Desktop/Freelance/Insurance%20-%20SK/modules/pdf.py), [static/script.js](file:///c:/Users/namsi/Desktop/Freelance/Insurance%20-%20SK/static/script.js) |
| **Dynamic Gemini Model Ranking & Failover** | `_score_model_for_intelligence` dynamically scores models from Google GenAI API. `get_best_models` ranks top models (e.g. 2.5-pro, 2.5-flash, 2.0-flash) and automatically fails over upon HTTP 429 Quota Exceeded. | [app.py](file:///c:/Users/namsi/Desktop/Freelance/Insurance%20-%20SK/app.py), [modules/utils.py](file:///c:/Users/namsi/Desktop/Freelance/Insurance%20-%20SK/modules/utils.py) |
| **Multi-Worker Ephemeral Asset Storage** | Ephemeral PDF previews and temporary damage photos use PostgreSQL private asset storage (`modules/assets.py`) with UUID tokens and TTL expiration, guaranteeing multi-worker consistency across Gunicorn processes. | [modules/assets.py](file:///c:/Users/namsi/Desktop/Freelance/Insurance%20-%20SK/modules/assets.py), `/assets/<token>/content` |
| **Surveyor Master Profile & Auto-Prefill** | Stores SLA No, License No, Category, Valid Up To, Bank Name, Account Number, IFSC, Branch, PAN, Mobile, Email. `get_last_surveyor_details` automatically pre-fills these values into new reports. | [db.py](file:///c:/Users/namsi/Desktop/Freelance/Insurance%20-%20SK/db.py), [app.py](file:///c:/Users/namsi/Desktop/Freelance/Insurance%20-%20SK/app.py) |
| **GSTR-1 & CA Multi-Column Excel Export** | Generates GSTR-1 B2B CSV and multi-column CA Excel (`.xlsx`) workbooks with GSTIN, Invoice Number, Taxable Value, CGST (9%), SGST (9%), IGST (18%), and Gross Total breakdown. | [app.py](file:///c:/Users/namsi/Desktop/Freelance/Insurance%20-%20SK/app.py), `/export_gstr1_excel` |
| **Gmail Intimation Sync & Cancellation** | Syncs claim intimations from Gmail via OAuth (Fernet-encrypted tokens), parses details into spot drafts, deduplicates claim numbers, and supports intimation cancellation. | [modules/gmail.py](file:///c:/Users/namsi/Desktop/Freelance/Insurance%20-%20SK/modules/gmail.py), [worker.py](file:///c:/Users/namsi/Desktop/Freelance/Insurance%20-%20SK/worker.py) |
| **Role Redaction & Workspace Isolation** | Survey Fee Register and financial KPIs are completely hidden from employee UI. Direct HTTP requests to `/api/insurers/next-invoice-no` return `403 Forbidden`. Claims are workspace-scoped (`workspace_admin_id`). | [app.py](file:///c:/Users/namsi/Desktop/Freelance/Insurance%20-%20SK/app.py), [static/script.js](file:///c:/Users/namsi/Desktop/Freelance/Insurance%20-%20SK/static/script.js) |

---

## 5. Security & Architectural Invariants

1. **CSRF Enforcement**: All state-modifying requests (POST, PUT, DELETE) must provide a valid CSRF token in header `X-CSRFToken` and/or `csrf_token` form field.
2. **Context Processors in Tests**: When instantiating secondary Flask app instances or test fixtures with `create_app()`, always copy template context processors: `new_app.template_context_processors = app.template_context_processors.copy()`.
3. **Async Job Offloading**: Never run synchronous heavy PDF generation, Gemini AI vision parsing, or Google Drive uploads in view request handlers. Offload to `modules/jobs.py` queue for execution by `worker.py`.
4. **Private Asset Isolation**: Never store sensitive user documents, uploads, or signatures under `/static`. All files must reside in `modules/assets.py` private database storage with workspace authorization.
5. **No ORM Rule**: Raw parameterized SQL queries with `psycopg2` or `sqlite3` only. Do not introduce SQLAlchemy or Peewee.

---

## 6. Systemd Units & Key Application Paths

- **Web App Service:** `/etc/systemd/system/insurance.service`  
  Command: `gunicorn --workers 3 --threads 4 --timeout 600 --bind 127.0.0.1:5000 app:app`
- **Async Worker Service:** `/etc/systemd/system/insurance-worker.service`  
  Command: `python worker.py`
- **Nginx Configuration:** `/etc/nginx/sites-available/skinsurance` (symlinked to `/etc/nginx/sites-enabled/`)
- **Environment File:** `/var/www/insurance-app/.env` (mode `600`, outside version control)
- **Automated Backup Cron:** `/etc/cron.daily/backup_insurance_db` (Runs `/var/www/insurance-app/vps_setup/backup_cron.sh`, 14-day rotation)
- **Client Manual & Release Notes (Markdown):** [docs/CLIENT_USER_MANUAL_AND_CHANGELOG.md](file:///c:/Users/namsi/Desktop/Freelance/Insurance%20-%20SK/docs/CLIENT_USER_MANUAL_AND_CHANGELOG.md)
- **Client User Manual (PDF):** [downloads/Motor_Survey_Software_User_Guide.pdf](file:///c:/Users/namsi/Desktop/Freelance/Insurance%20-%20SK/downloads/Motor_Survey_Software_User_Guide.pdf) (9.4 KB)

---

## 7. Retired & Obsolete Technologies (Do Not Use)

- **Legacy Cloudflare Quick Tunnels (`trycloudflare.com`)**: Fully retired. Traffic routes directly via DNS A-records (`skinsurance.tech` -> `185.199.52.85`) with Nginx and Let's Encrypt SSL.
- **Single-User License Key Validation (`license_key`)**: Fully removed. Replaced by Admin-scoped Multi-tenant Workspace model (`workspace_admin_id`).
- **cPanel / Hostinger Shared Hosting**: Fully migrated to dedicated Ubuntu 24.04 VPS with PostgreSQL 14+ and Gunicorn.

---

## 8. Verification & CLI Commands

### Automated Test Suite
Run all 181 unit, integration, and security tests:
```bash
.\.venv\Scripts\python.exe -m pytest
```

### Server Health Check
Verify live application liveness and SSL:
```bash
curl -fsS https://skinsurance.tech/healthz
```

### Manual Database Snapshot Command
```bash
export PGPASSWORD='surveyorportal@2026' && pg_dump -U insurance_user -h localhost -d insurance_db > /root/backups/insurance_db_manual_$(date +%Y%m%d_%H%M%S).sql
```

### User Administration CLI
```bash
cd /var/www/insurance-app
sudo venv/bin/flask promote-admin <username>
sudo venv/bin/flask create-employee <username> <temp-password> --admin <admin-username> [--gmail-sync]
```