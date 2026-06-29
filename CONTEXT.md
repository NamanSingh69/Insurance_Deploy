# Context: Motor Survey Report Generator (VPS Hosting)

## Project Overview
The **Motor Survey Report Generator** is a Python Flask web application designed for insurance surveyors. It processes claim files, vehicle photographs, and documents using Gemini AI to automatically extract key values and render detailed PDF survey reports.

## System Architecture & State
* **Application Server:** Single instance deployed on a **Hostinger VPS (KVM 1)** running **Ubuntu 24.04 LTS**.
* **Database:** Local **PostgreSQL** database hosted directly on the VPS for zero query latency (replacing Australia-hosted Supabase free tier).
* **Storage:** Report PDFs and vehicle photos are uploaded to **Google Drive** using a Service Account configured in `.env`.
* **Process Manager:** Gunicorn running via a Systemd service (`insurance.service`) proxying traffic locally.
* **Web Server:** Nginx running as a reverse proxy, listening on Port 80.
* **Public Access Bypass:** Bypassed Hostinger inbound network drop using Cloudflare Tunnel. The site is publicly visible at: **https://pricing-themselves-console-intervals.trycloudflare.com/**

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
* **Hostinger Firewall:** Firewall `319602` is activated and synced with rules allowing TCP 22, 80, 443, 8000 (source: any). Configured via Hostinger API using bearer token.
* **OS Firewall:** `ufw` is inactive. `iptables` INPUT policy is ACCEPT with no rules. No OS-level blocking.
* **Services Verified:** SSH (port 22), Nginx (port 80), Gunicorn (port 8000) all listening on `0.0.0.0`. App returns HTTP 302 when curled from within VPS.
* **Blocked Seam:** Port 80 and Port 22 connections to the public IP `185.199.52.85` are **still timing out** from external networks.
  * **Root Cause:** Hostinger datacenter-level networking issue. Traceroute shows traffic dying at the Hostinger DC edge (hop 12). The VPS can reach itself via public IP, but external traffic is dropped before reaching the VM. This is NOT a configuration issue — tested with firewall active, inactive, different firewalls, and VPS restart. All produce the same timeout.
  * **Next Step:** Contact Hostinger support with this diagnostic evidence. Reference VPS ID `1789781`, IP `185.199.52.85`, firewall ID `319602`.
* **Resolution (Bypass):** Installed `cloudflared` on the VPS to establish a secure Cloudflare Tunnel, exposing the app (Port 80) directly to the web. Verified login rendering and database authentication successfully at: **https://pricing-themselves-console-intervals.trycloudflare.com/**. Added cleanup scripts to verify database integrity.
