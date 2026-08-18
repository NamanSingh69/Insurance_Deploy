# Requirements Document: Client-Requested Enhancements & RBAC Hardening
**Date:** August 18, 2026  
**Document ID:** `requirements_2026_08_18.md`  
**System:** Motor Survey Report Generator (`https://skinsurance.tech`)  

---

## Executive Summary
This document formalizes the client-requested role and access refinements for the Motor Survey Report Generator. The system enforces a three-tier operational structure:
1. **Primary Client Administrator (`SKANOWAR`):** The primary account for surveyor Sk Anowar Ali with complete workspace ownership, financial KPI visibility, CA GSTR-1/Excel tax exports, report/fee deletion privileges, and staff user management.
2. **Developer Administrator (`NAMAN`):** Dedicated developer maintenance account.
3. **Employee / Field Staff (`USER`):** Operational assistant account linked to `SKANOWAR`'s workspace, empowered to search, create, and edit claims/reports, upload photos, draft fee bills, and download PDFs, while strictly restricted from deleting records, viewing aggregate corporate revenue metrics, or downloading CA tax accounting exports.

---

## Numbered Requirements

### R1: Primary Client Admin Provisioning & Unified Workspace Ownership
- **Source:** User Request #2 (`"create a new admin user, which would be the main account the client will use (which will show all the reports in the USER account)"`)
- **Quote:** *"create a new admin user, which would be the main account the client will use (which will show all the reports in the USER account)"*
- **App Area:** `Admin settings` | `Dashboard` | `Reports` | `Claim Register` | `Survey Fee Register`
- **Interpretation:**
  - Provision account `SKANOWAR` with default password `AnowarAdmin@2026` and `role = 'admin'`.
  - Flag `must_change_password` set to `FALSE` upon provisioning so login and all dashboard APIs function immediately without 403 blocks.
  - Automatically populate surveyor master profile details (License `SLA-121784`, Membership `L/E/10721`, Address, Contact, Email `skanowarali93@gmail.com`).
  - Unify workspace data so all historical reports, fee bills, and claim records belong to `SKANOWAR`'s workspace (`workspace_admin_id`), allowing the client to see all reports and fee bills.
- **Ambiguities:** None.
- **Risk Rating:** Medium (Requires database workspace re-scoping and user state self-healing).

---

### R2: Developer Admin Account Preservation (`NAMAN`)
- **Source:** User Request #2 (`"my account (NAMAN) is just for the developer"`)
- **Quote:** *"my account (NAMAN) is just for the developer"*
- **App Area:** `Admin settings`
- **Interpretation:**
  - Preserve `NAMAN` / `69420` as an active developer admin account.
  - Keep development and technical diagnostics isolated so standard operational claims reside in the client's business workspace.
- **Ambiguities:** None.
- **Risk Rating:** Low.

---

### R3: Employee Fee Register Access & Operational Drafting (`USER`)
- **Source:** User Request #2 & #4 (`"the employee should be able to see the fee resgister button but with the restrictions as stated"`)
- **Quote:** *"a normal employee should be able to search for, create, and edit but not delete or see al survey fee register"* / *"the employee should be able to see the fee resgister button but with the restrictions as stated"*
- **App Area:** `Survey Fee Register` | `Dashboard` | `Exports`
- **Interpretation:**
  - **Navigation & UI:** Display the *Survey Fee Register* navigation tab button in the header (`#tab-btn-fees`) and home card (`#open-fees-btn`) for employee users.
  - **Operational Drafting:** Allow employees to view fee register bills in their assigned workspace, search fee bills, create/save fee bills (`POST /api/fee_bills`), fetch the next sequential invoice number (`GET /api/next_invoice_no`), and generate/download Fee Bill PDFs (`POST /generate_fee_pdf`, `GET /api/fee_bills/<id>/pdf`).
  - **Deletion Restriction:** Hide the Delete action button in the fee bills table for employees; enforce `@admin_required` on `DELETE /api/fee_bills/<id>` returning `403 Forbidden` for non-admins.
  - **Financial Redaction:** Hide aggregate financial metrics (`#financial-dashboard` KPI cards: Total Invoiced, Amount Received, Outstanding Fees) from employee UI. Direct HTTP requests to `/api/fees_summary` must return `403 Forbidden`.
  - **Tax Export Protection:** Hide the CA Multi-Column Excel and GSTR-1 CSV download buttons (`#financial-export-section`) from employee UI. Direct HTTP requests to `/download_fees_excel`, `/download_gstr1_csv`, and `/export_gstr1_excel` must return `403 Forbidden`.
- **Ambiguities:** None.
- **Risk Rating:** High (Strict financial confidentiality and RBAC enforcement required).

---

### R4: Saved Reports Deletion Restriction for Employees
- **Source:** User Request #2 (`"a normal employee should be able to search for, create, and edit but not delete"`)
- **Quote:** *"a normal employee should be able to search for, create, and edit but not delete"*
- **App Area:** `Reports` | `Claim Register`
- **Interpretation:**
  - Employees have full permissions to search, view, create, and edit motor survey reports and upload damage photos.
  - Employees MUST NOT be permitted to delete saved reports.
  - In the UI, the `Delete` button in the Saved Reports table is rendered only when `role === 'admin'`.
  - Backend route `DELETE /delete_report/<report_id>` is protected with `@admin_required`, returning `403 Forbidden` (`{"error": "Administrator access is required."}`) if an employee attempts deletion.
- **Ambiguities:** None.
- **Risk Rating:** Low.

---

### R5: Reliable CI/CD Automated Deployment & Self-Healing Service Lifecycle
- **Source:** User Request #5 & Goal Instruction (`"fee bill, reports, etc. still not visible, verify all functionality works /goal"`)
- **Quote:** *"fee bill, reports, etc. still not visible, verify all functionality works /goal"*
- **App Area:** `Admin settings` | `Infrastructure` | `Database`
- **Interpretation:**
  - Automated deployment triggered via `python scripts/deploy.py` or `POST /api/deploy-webhook` must reliably fetch latest commits, run SQL migrations, ensure default user accounts and workspace associations, and restart Gunicorn/worker services smoothly.
  - Add self-healing logic so that whenever `PostgresDB.connect()` executes, `SKANOWAR` is provisioned as `admin` with `must_change_password = False` and workspace data linked.
- **Ambiguities:** None.
- **Risk Rating:** Medium.

---

## App Area Traceability Matrix

| Requirement | App Area | Frontend Seams | Backend Endpoints / Files | Database / Model Impact |
|---|---|---|---|---|
| **R1** | Admin settings, Reports, Fee Register | Login modal, Profile drawer, Dashboard cards | `app.py` (`login`, `load_user`), `db.py` | `users` table (`SKANOWAR`), `reports` & `fee_bills` (`workspace_admin_id`) |
| **R2** | Admin settings | N/A | `app.py` | `users` table (`NAMAN`, role `admin`) |
| **R3** | Fee Register, Dashboard, Exports | `#tab-btn-fees`, `#open-fees-btn`, `#financial-dashboard`, `#financial-export-section` | `app.py` (`/api/fee_bills`, `/api/next_invoice_no`, `/generate_fee_pdf`, `/api/fees_summary`) | `fee_bills` table, RBAC decorators (`@login_required` vs `@admin_required`) |
| **R4** | Reports, Claim Register | `.delete-report-btn`, Saved Reports table | `app.py` (`/delete_report/<id>`) | RBAC enforcement (`@admin_required`) |
| **R5** | Infrastructure, DB Migrations | N/A | `vps_setup/auto_deploy.sh`, `app.py` (`deploy_webhook`), `db.py` | `schema_migrations`, self-healing provisioning |

---

## Next Steps (Phase 2 & Phase 3)
Upon approval of this requirements document:
1. Proceed with Phase 2 (Implementation Plan) detailing specific file diffs, routes, and verification steps.
2. Execute Phase 3 implementation, run the full 184+ test suite, deploy to production VPS, and visually verify all behaviors as both admin (`SKANOWAR`) and employee (`USER`).
