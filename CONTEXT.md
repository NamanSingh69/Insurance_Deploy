# Project Context: Motor Survey Report Generator

This document provides a comprehensive technical overview of the **Motor Survey Report Generator** application. It describes the complete software stack, database schema, file layout, dynamic AI model integration, and the current Hostinger VPS deployment infrastructure.

---

## 1. System Architecture Overview

The Motor Survey Report Generator is a multi-user, web-based tool designed for insurance surveyors. It streamlines the creation of survey reports by automatically parsing insurance claims documents, parts invoices, and vehicle photographs using Gemini AI, generating consolidated PDFs, and storing structured records.

```mermaid
graph TD
    User([Surveyor User])
    Client[Web Browser (HTML/CSS/JS)]
    Proxy[Nginx Reverse Proxy]
    WSGI[Gunicorn HTTP Server]
    App[Flask App Logic]
    DB[(Local PostgreSQL)]
    Drive[(Google Drive API)]
    Gemini[Google Gemini API]
    
    User -->|HTTPS| Client
    Client -->|Port 80/443 via Cloudflare Tunnel| Proxy
    Proxy -->|Local Port 5000| WSGI
    WSGI --> App
    App -->|Local Port 5432| DB
    App -->|JSON/File Stream| Drive
    App -->|JSON Prompt| Gemini
```

---

## 2. Technical Stack Details

### Frontend Layer
* **Tech Stack:** HTML5, CSS3 (Vanilla), JavaScript (ES6+).
* **Styling Framework:** Custom responsive layout styled inside `static/style.css`.
* **Icons:** Font Awesome v6.4.0 (CDN-loaded).
* **Pages:**
  * `login.html`: Secure user authentication page.
  * `index.html`: Main dashboard page. Contains:
    * Reports list table (paginated search, sort, and status toggles).
    * Core Survey Report Entry forms (Surveyor profile, claim details, policy information, vehicle descriptors).
    * Vehicle parts tables (Metal, Plastic, Glass, Endorsement tables with automatic depreciation and salvage calculations).
    * Media uploading component (invoice and vehicle photograph selectors).
    * Surveyor Profile and Dynamic Settings modals.
* **Client-Side Scripts:**
  * `static/script.js` handles form states, dynamic table insertions, real-time calculations (depreciation percentages, VAT/GST additions, salvage values), uploads via Drive resumable URLs, and dynamic model lists population on opening settings.

### Backend Layer
* **Tech Stack:** Python Flask (v3.1.0).
* **WSGI Server:** Gunicorn (v23.0.0) configured with 3 workers.
* **Process Monitor:** Systemd service (`insurance.service`).
* **Web Server:** Nginx (v1.24) acting as a local reverse proxy (routing requests to Gunicorn port `5000` and serving `/static/` assets directly with a 30-day cache control).
* **Security Controls:**
  * **Flask-Login (v0.6.3):** Manages user session state and secure HTTP-Only/SameSite session cookies.
  * **Flask-Bcrypt (v1.0.1):** Secure password hashing using salt rounds.
  * **Flask-Limiter (v3.8.0):** Limits brute force attacks (rate-limits endpoints to 200/day, 50/hour).
  * **File Upload Limits:** Configured up to 100MB (`MAX_CONTENT_LENGTH`).

### Database Layer
* **Database Engine:** PostgreSQL (local instance on Port 5432).
* **Connection Client:** `psycopg2-binary` (v2.9.9).
* **Tables:**
  1. `users` Table:
     * `id` (SERIAL PRIMARY KEY)
     * `username` (VARCHAR(255) UNIQUE) — User login credential.
     * `password_hash` (VARCHAR(255)) — Bcrypt password hash.
     * Profile Metadata: `full_name`, `qualifications`, `designation`, `license_no`, `expiry_date`, `membership_no`, `address_line_1`, `address_line_2`, `address_line_3`, `contact_no`, `email`.
     * Dynamic settings: `gemini_api_key` (VARCHAR(255)) & `gemini_model` (VARCHAR(255)) which store user-specific AI preferences.
  2. `reports` Table:
     * `id` (VARCHAR(255) PRIMARY KEY) — Unique UUID4 key.
     * `user_id` (INTEGER REFERENCES users(id)) — Links report to the surveyor user.
     * Report Quick Fields: `report_no`, `insured_name`, `vehicle_no`, `claim_no`, `policy_no`.
     * `saved_at` (TIMESTAMP) — Date of save.
     * `include_in_consolidated` (BOOLEAN) — Status flag.
     * `report_data_json` (JSONB) — Native JSON column containing the entire nested report data payload (depreciation, lists of parts, images metadata, descriptions).

### AI Integration Layer (Gemini AI)
* **Client Library:** `google-generativeai` (v0.8.4).
* **Resolution Workflow (`get_generative_models`):**
  1. Priority 1: Reads `user.gemini_api_key` from the database.
  2. Priority 2: Falls back to the server environment's `GEMINI_API_KEY`.
  3. Model Selection: If `user.gemini_model` is explicitly selected in settings (e.g. `gemini-1.5-pro` or `gemini-1.5-flash`), that model is instantiated. If not, the application calls `get_user_best_models` which queries `genai.list_models()`, filters for content generation capability, and scores them using the intelligence heuristic `_score_model_for_intelligence` (preferring Pro over Flash, and thinking/reasoning models over standard versions).

### File Storage Layer (Google Drive)
* **API Clients:** `google-auth` (v2.38) & `gspread` (v6.0.2) using a shared Google Service Account.
* **Credentials:** Read from `GOOGLE_SHEETS_CREDENTIALS` (JSON string) and `GOOGLE_DRIVE_FOLDER_ID` (target root folder).
* **Directory Structure:**
  * The system automatically creates a root folder called `Survey Reports/`.
  * For each report, it creates a subdirectory named after the vehicle's registration number (e.g., `Survey Reports/MH02AB1234/`).
  * All uploaded vehicle photos, estimate sheets, invoices, and the final compiled report PDF are stored inside this vehicle-specific folder.

### File Generation Layer
* **PDF Reports:** Generated dynamically in Python using `fpdf2` and `reportlab` layout libraries. Builds headers, surveyor details, calculation tables, deprecation breakdowns, and dynamically fetches and embeds vehicle photographs uploaded to Google Drive.
* **Consolidated Outputs:** Exports multiple reports simultaneously in Microsoft Excel/CSV format via `/download_consolidated_csv`.

---

## 3. Codebase File Index

* **[app.py](file:///c:/Users/namsi/Desktop/Freelance/Insurance%20-%20SK/app.py):** Main application routing, Flask settings, authentication logic, Gemini AI integration, report calculation handling, PDF rendering layout, and file download controllers.
* **[db.py](file:///c:/Users/namsi/Desktop/Freelance/Insurance%20-%20SK/db.py):** PostgreSQL interface file. Connects to the local DB, initializes database schemas, updates and creates user accounts, fetches user metadata only (for fast listing), processes report CRUD requests, and hosts Google Drive folder/file upload wrappers.
* **[migrate_db.py](file:///c:/Users/namsi/Desktop/Freelance/Insurance%20-%20SK/migrate_db.py):** Data migration utility script. Migrates users and reports from the legacy Vercel/Sheets CSV backups (`InsuranceAppDB - Users.csv` and `InsuranceAppDB - Reports.csv`) to PostgreSQL, consolidating chunked data blocks back into native JSONB fields.
* **[sheets_db.py](file:///c:/Users/namsi/Desktop/Freelance/Insurance%20-%20SK/sheets_db.py):** Legacy database provider that used Google Sheets as a storage engine. Replaced by `db.py` but preserved in the repository as a design backup.
* **[vps_setup/](file:///c:/Users/namsi/Desktop/Freelance/Insurance%20-%20SK/vps_setup):**
  * `setup_vps.sh`: Installs system packages, Python venv, PostgreSQL, Nginx, Certbot, Git, and sets up database credentials.
  * `nginx.conf`: Nginx server configuration reverse-proxying port 80 to port 5000.
  * `insurance.service`: Gunicorn systemd daemon manager.
* **[templates/](file:///c:/Users/namsi/Desktop/Freelance/Insurance%20-%20SK/templates):** Contains Jinja2 HTML templates (`index.html` and `login.html`).
* **[static/](file:///c:/Users/namsi/Desktop/Freelance/Insurance%20-%20SK/static):** Contains frontend assets (`style.css`, client script `script.js`, and system graphics `favicon.png`/`header.png`).
* **[tests/](file:///c:/Users/namsi/Desktop/Freelance/Insurance%20-%20SK/tests):** Contains local end-to-end integration and routing tests.

---

## 4. Hostinger VPS Infrastructure & Deployment State

* **Server Profile:** Hostinger KVM 1 VPS instance running **Ubuntu 24.04 LTS**.
* **Internal IP Routing:** Server is correctly configured with local interfaces, and Gunicorn is running on port 8000. Nginx is listening on port 80 and reverse-proxying.
* **Public Network Drop (IPv4):** Connections directly to the VPS IPv4 `185.199.52.85` on port 80/22/443 from external networks time out. Hostinger's edge routers drop all incoming IPv4 TCP handshake requests before reaching the VM.
* **Direct Network Access (IPv6 Bypass):** Incoming IPv6 traffic is **fully open and unblocked** on the edge routers. The VPS is reachable directly from external networks via its public IPv6 address:
  * **IPv6 Address:** `2a02:4780:12:aa78::1`
  * **Listening Ports:** SSH (22), HTTP (80), HTTPS (443) are all verified accessible externally over IPv6.
* **Production Database Backup:** A verified binary dump of the PostgreSQL database (4 users, 241 reports) was taken and saved to the local machine:
  * **Backup file name:** `db_backup.dump`
  * **Dumping tool:** `pg_dump`
* **Direct Routing Implementation Plan:**
  1. Add/modify the custom domain's **AAAA record** in the domain registrar's DNS management (the domain `iitpcep.online` is registered under a different Hostinger account than the VPS) pointing directly to the VPS IPv6: `2a02:4780:12:aa78::1`.
  2. Run Certbot on the VPS via IPv6 to generate a standard Let's Encrypt SSL certificate for the domain.
  3. Optionally enable Cloudflare proxying (orange cloud CDN) on the domain. This acts as an IPv4-to-IPv6 proxy, allowing IPv4-only users to connect to Cloudflare edge nodes, which then proxy the traffic to the VPS via IPv6. This requires no software tunnels running on the VPS.
* **Legacy Cloudflare Tunnel Bypass:** The systemd service `cloudflared.service` is configured as a backup bypass tunnel using token-based authentication.

