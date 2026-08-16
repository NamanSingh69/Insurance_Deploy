# Motor Survey Report Generator — Complete Architecture & Operations Context

**Production Domain:** [https://skinsurance.tech](https://skinsurance.tech)  
**Target User / Surveyor:** Sk Anowar Ali  
**Core Framework:** Python 3.12+, Flask 3.1, Gunicorn 23.0, PostgreSQL 14+, Redis, Nginx Reverse Proxy (Let's Encrypt SSL).

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
- **Administrator Account:** `NAMAN` / `69420` (ID: 2)
  - Full workspace access, financial Survey Fee Register, Insurer Master management, GSTR-1/CA Excel exports, user promotions, and system settings.
- **Employee Account:** `USER` / `UH65A#DF` (ID: 1, `admin_id`: 2)
  - Operational claim management, survey report editing, PDF downloads.
  - **Financial Redaction:** Fee Register tabs and financial KPI metrics are completely hidden from UI; API requests to financial routes return `403 Forbidden`; claim saves cannot overwrite fee records.

---

## 2. Automated CI/CD & Zero-Friction Deployment Pipeline

### How Deployment Works (Push-to-Deploy)
The deployment process is **100% automated**. Pushing code to `origin/main` automatically updates production in **~3.5 seconds** with zero manual server interaction:

```bash
git add -A
git commit -m "your commit message"
git push origin main
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

---

## 3. Dynamic Asset Cache-Busting

- **Context Processor:** In [app.py](file:///c:/Users/namsi/Desktop/Freelance/Insurance%20-%20SK/app.py), `inject_request_security_values` extracts the active Git commit hash (`git rev-parse --short HEAD`) and exposes it to Jinja templates as `app_version`.
- **Template Binding:** In [templates/index.html](file:///c:/Users/namsi/Desktop/Freelance/Insurance%20-%20SK/templates/index.html) and [templates/login.html](file:///c:/Users/namsi/Desktop/Freelance/Insurance%20-%20SK/templates/login.html):
  - Stylesheet: `{{ url_for('static', filename='style.css') }}?v={{ app_version }}`
  - Script: `{{ url_for('static', filename='script.js') }}?v={{ app_version }}`
- **Benefit:** Client browsers and Cloudflare/Nginx CDN caches immediately invalidate upon new commits, preventing stale JavaScript/CSS bugs.

---

## 4. Key Feature Implementations (R1–R6 Matrix)

| Requirement | Implementation Detail | Technical Seam |
|---|---|---|
| **R1: In-Place Dashboard Drilldown** | Clicking KPI cards (*Pending claims*, *Inspection pending*, *Documents awaited*) renders filtered claim lists directly below cards in `#dashboard-drilldown-section` without tab switching. Active card receives `.active-metric-card` highlight border. | `static/script.js` (`renderDashboardDrilldown`), `#dashboard-drilldown-section` |
| **R2: Missing Documents Checklist Modal** | Clicking `Docs` button in Claim Register opens `#pending-documents-modal` with granular item checklists, instant toggle updates, and automated reminder counter. Zero console errors. | `static/script.js` (`openPendingDocsModal`), `#pending-documents-modal` |
| **R3: Master Insurer Guidance & Setup** | Survey Fee Register includes guidance banner and `+ Manage Insurer Masters` quick action (`.open-insurer-master-modal-btn`) launching `#insurer-master-modal` to configure master insurer records (GSTIN, Address, Default Rate/Km, Prefix). | `static/script.js` (`loadInsurerMasters`), `#insurer-master-modal` |
| **R4: Smart Auto-Prefix & Sequential Invoicing** | Typing insurer name (e.g. *National Insurance Company*) auto-derives smart uppercase prefix (e.g. `NIC-0001`, `OGI-0001`), auto-fills GSTIN & address, and fetches next sequential invoice number from `/api/insurers/next-invoice-no`. | `static/script.js` (`deriveInsurerAcronym`, `handleFeeInsurerInput`), `/api/insurers/next-invoice-no` |
| **R5: Whole Rupee Stepper & Live Summary** | Professional fee input enforces integer step (`step="1"`). Live summary card (`#fee-live-calc-box`) dynamically recalculates: $\text{Taxable} = \text{Prof} + \text{Conv} + \text{Photo}$, $\text{GST (18\%)}$, $\text{Gross Total}$. | `static/script.js` (`updateLiveFeeSummary`), `#fee-live-calc-box` |
| **R6: Photo Upload Rate Limiting & Diagnostics** | HD damage photo uploader supports batch drag-and-drop with adaptive client throttling. Replaced false Google Drive quota alerts with accurate server error diagnostics. | `static/script.js` (Upload dropzones), Flask-Limiter config |
| **Role Redaction Guard** | Survey Fee Register tab and financial KPI metrics are completely hidden from employee UI. Direct HTTP requests to `/api/insurers/next-invoice-no` return `403 Forbidden`. | [app.py](file:///c:/Users/namsi/Desktop/Freelance/Insurance%20-%20SK/app.py) (`is_admin_user` checks), `static/script.js` (`initMotorSurveyWorkspace`) |

---

## 5. Systemd Units & Key Application Paths

- **Web App Service:** `/etc/systemd/system/insurance.service`  
  Command: `gunicorn --workers 3 --threads 4 --timeout 600 --bind 127.0.0.1:5000 app:app`
- **Async Worker Service:** `/etc/systemd/system/insurance-worker.service`  
  Command: `python worker.py`
- **Nginx Configuration:** `/etc/nginx/sites-available/skinsurance` (symlinked to `/etc/nginx/sites-enabled/`)
- **Environment File:** `/var/www/insurance-app/.env` (mode `600`, outside version control)
- **Automated Backup Cron:** `/etc/cron.daily/backup_insurance_db` (Runs `/var/www/insurance-app/vps_setup/backup_cron.sh`, 14-day rotation)
- **Client Manual & Release Notes (Markdown):** [docs/CLIENT_USER_MANUAL_AND_CHANGELOG.md](file:///c:/Users/namsi/Desktop/Freelance/Insurance%20-%20SK/docs/CLIENT_USER_MANUAL_AND_CHANGELOG.md)
- **Client User Manual (PDF):** [downloads/Motor_Survey_Software_User_Guide.pdf](file:///c:/Users/namsi/Desktop/Freelance/Insurance%20-%20SK/downloads/Motor_Survey_Software_User_Guide.pdf) (9.4 KB)
- **Evidence Screenshots:** `docs/` (`evidence_r1_...` through `evidence_r6_...`, `evidence_employee_financial_redaction.png`, `webhook_...png`)

---

## 6. Verification & CLI Commands

### Automated Test Suite
Run all 177 unit, integration, and security tests:
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