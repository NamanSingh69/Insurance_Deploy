# Context: Motor Survey Report Generator (VPS Hosting)

## Project Overview
The **Motor Survey Report Generator** is a Python Flask web application designed for insurance surveyors. It processes claim files, vehicle photographs, and documents using Gemini AI to automatically extract key values and render detailed PDF survey reports.

## System Architecture & State
* **Application Server:** Single instance deployed on a **Hostinger VPS (KVM 1)** running **Ubuntu 24.04 LTS**.
* **Database:** Local **PostgreSQL** database hosted directly on the VPS for zero query latency (replacing Australia-hosted Supabase free tier).
* **Storage:** Report PDFs and vehicle photos are uploaded to **Google Drive** using a Service Account configured in `.env`.
* **Process Manager:** Gunicorn running via a Systemd service (`insurance.service`) proxying traffic locally.
* **Web Server:** Nginx running as a reverse proxy, listening on Port 80.

---

## Technical Details

### VPS Credentials
* **Host IP:** `185.199.52.85`
* **Username:** `root`
* **Password:** `surveyorportal@2026`
* **SSH Port:** `22`

### App File Structure
* **App Directory:** `/var/www/insurance-app`
* **Virtual Environment:** `/var/www/insurance-app/venv`
* **Environment Configuration:** `/var/www/insurance-app/.env`
* **Service Config:** `/etc/systemd/system/insurance.service`
* **Nginx Server Block:** `/etc/nginx/sites-available/insurance`
* **Github Repository:** `https://github.com/NamanSingh69/Insurance_Deploy.git`

### Database Details
* **DB Engine:** PostgreSQL (local instance on port 5432)
* **Database Name:** `insurance_db`
* **DB User:** `insurance_user`
* **DB Password:** `surveyorportal@2026`
* **Connection String:** `postgresql://insurance_user:surveyorportal@2026@localhost/insurance_db`

---

## Migration & Deployment Progress
* **Code Setup:** Local updates (Procfile, vps_setup configurations, dynamic Gemini API key user settings, and CLI create-user command) have been committed and pushed to `origin/main` on GitHub, and successfully pulled on the VPS.
* **Server Dependency Setup:** Installed PostgreSQL, Nginx, Certbot, Git, and Python. Virtual environment built and dependencies successfully installed on the VPS.
* **Database Initialization:** Run the database schema connector. Tables `users` and `reports` exist.
* **Data Migration:** Run `pg_dump` on the old Australia Supabase DB and `pg_restore` on localhost. Validated count results: **2 users and 241 reports** are successfully migrated.
* **Process Execution:** Nginx is running and Gunicorn is active on port 8000.
* **Blocked Seam:** Port 80 and Port 22 connections to the public IP `185.199.52.85` are currently timing out.
  * **Cause:** The Hostinger dashboard firewall has 0 rules allowing TCP 80/22. Rule TCP 443 was successfully added in the dashboard, but rules for TCP 80 and TCP 22 must be created and synchronized to make the site and SSH accessible.
