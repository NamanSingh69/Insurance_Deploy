# Requirements Document — Client Changes Request (2026-08-21)

**Project:** Motor Survey Report Generator ([https://skinsurance.tech](https://skinsurance.tech))  
**Target Client:** Sk Anowar Ali (Surveyor & Loss Assessor)  
**Date:** 21 August 2026 (Night Session — 21:35 IST)  
**Status:** 🛑 **STOP POINT — Awaiting User Approval (PHASE 1)**

---

## 1. Executive Summary & Media Ingestion Log (Phase 0)

All media files located in `Downloads/client changes request/` have been listed and ingested natively end-to-end via multimodal analysis. Zero policyholder PII has been transmitted to external services.

### Complete Media Files Ingestion Table

| # | File Name | Type | Size / Duration | Sender | Core Subject / Evidence Captured |
|---|---|---|---|---|---|
| 1 | `WhatsApp Image 2026-08-21 at 8.12.04 AM.jpeg` | Image (.jpeg) | 17.8 KB | Sk Anowar Ali (Client) | Screenshot of Survey Fee Register table row (`Invoice UIC-1`, `Report UIIC/2026/02`, `Claim 3126240110`, `United India Insurance Co.`) showing Actions column containing only `[👁 PDF]` and `[💳 Payment]`. Caption: *"Edit option hatgaya"*. |
| 2 | `Screenshot 2026-08-21 211510.png` | Image (.png) | 515.7 KB | Naman / Sk Anowar Ali | WhatsApp chat thread overview showing: (1) 8:12 AM message *"Edit option hatgaya"*, (2) 8:24 AM video (0:22), (3) 8:42 AM video (2:25), (4) 4:36 PM photo of Gemini API key error. |
| 3 | `WhatsApp Video 2026-08-21 at 8.24.23 AM.mp4` | Video (.mp4 + audio) | 2.1 MB / 00:22 | Sk Anowar Ali (Client) | Screen recording in Insurer Master Control Panel modal (`#insurer-master-modal`). Client clicks "Delete" on `United India Insurance Co., Kalyannagar`, confirms browser dialog, but row fails to delete. Audio: *"Ye Insurer Master Control Panel, yahan par ye cheez delete nahi ho raha... Isko theek kijiye."* |
| 4 | `WhatsApp Video 2026-08-21 at 8.42.44 AM.mp4` | Video (.mp4 + audio) | 15.2 MB / 02:25 | Sk Anowar Ali (Client) | Screen recording demonstrating two key items: (1) In Claim Register, filling New Claim form (`Claim No: 060088312000101NC077`, `PINAKI SAHA`, `WB-52-BD-2799`) and clicking "Create Claim" clears fields but fails to persist in table or dashboard; (2) Feature request to upload insurer appointment/intimation emails & PDFs directly in Claim Register to auto-populate the New Claim form. |
| 5 | `WhatsApp Image 2026-08-21 at 4.36.24 PM.jpeg` | Image (.jpeg) | 111.8 KB | Sk Anowar Ali (Client, logged in as `USER`) | High-res photo of laptop screen showing error on PDF upload (`Tarun Debnath (1).pdf`): `Error processing PDF: The background task could not be completed: 400 INVALID_ARGUMENT. ... API key not valid. Please pass a valid API key.` |

---

## 2. Requirements Specification (R1 – R5)

### R1: Survey Fee Register — Restore Missing "Edit" Action Button in Fee Register Table
- **Source:**
  - `WhatsApp Image 2026-08-21 at 8.12.04 AM.jpeg`
  - `Screenshot 2026-08-21 211510.png` (8:12 AM message: *"Edit option hatgaya"*)
- **Exact Quote / Transcript (Hindi):**
  > *"Edit option hatgaya"*
- **Interpretation & Functional Requirement:**
  1. **Context / Problem:** When adding the new `[💳 Payment]` status button during the previous update, the `[✏️ Edit]` button in the Survey Fee Register table (`#fee-register-tbody`) was omitted from the row actions column. As a result, users cannot reload a previously saved fee bill back into the form to make corrections or adjustments.
  2. **UI & Table Actions (`#fee-register-tbody`):**
     - Re-introduce `<button type="button" class="btn btn-primary btn-sm edit-fee-bill-btn" data-bill-id="${escapeHtml(bill.id)}" title="Edit Fee Bill" style="margin-left: 4px;"><i class="fas fa-edit"></i> Edit</button>` in the Actions column of each fee bill row (alongside `[👁 PDF]`, `[💳 Payment]`, and `[🗑 Delete]`).
  3. **Edit Interaction & Form Pre-Fill (`editFeeBill(billId)`):**
     - Clicking "Edit" retrieves the fee bill object from `currentFeeBillsList` (or `/api/fee_bills/<id>`), populates all form fields in `#fee-register-form`:
       - `fee-bill-id` (hidden field for upsert/update)
       - `fee-report-id`, `fee-report-no`
       - `fee-invoice-no`, `fee-invoice-date`
       - `fee-insurer`, `fee-insurer-gst`, `fee-surveyor-code`, `fee-insurer-address`
       - `fee-policy-no`, `fee-claim-no`, `fee-vehicle-no`, `fee-insured`, `fee-date-of-accident`
       - All 8 itemized fee breakdown checkboxes, amounts, route descriptions, KM values, rate/km
       - GST %, include signature toggle, payment status, and invoice status.
     - Automatically calls `updateLiveFeeSummary()` and scrolls smoothly to the top of `#fee-register-form`.
     - Saving the form updates the existing fee bill record without generating duplicate invoice entries.
- **Ambiguities & Trade-Offs:**
  - Updating an existing fee bill preserves its assigned `invoice_no` and payment lifecycle history unless explicitly changed.
- **Risk Rating:** Low
- **App Area:** `Survey Fee Register`

---

### R2: Insurer Master Control Panel — Fix Insurer Master Record Deletion for Workspace Accounts
- **Source:**
  - `WhatsApp Video 2026-08-21 at 8.24.23 AM.mp4` (0:00 – 0:22)
- **Exact Quote / Transcript (Hindi):**
  > *"Ye Insurer Master Control Panel, yahan par ye cheez delete nahi ho raha. Ye dekhiye... Delete... OK... but delete nahi ho raha hai... Isko theek kijiye."*
- **Interpretation & Functional Requirement:**
  1. **Context / Problem:** In `app.py` line 4943, `DELETE /api/insurers/<id>` strictly enforces `if not is_admin_user(current_user): return jsonify({'error': 'Admin permission required.'}), 403`. When the client or assistant logs in as `USER` (an employee in `SKANOWAR`'s workspace) and attempts to delete a duplicate insurer record (e.g. `United India Insurance Co., Kalyannagar`), the server rejects the deletion with `403 Forbidden`, while the frontend modal displays no feedback, causing the record to persist.
  2. **Authorization & Multi-Tenant Scoping (`app.py` & `db.py`):**
     - Update `DELETE /api/insurers/<id>` to allow workspace members within their assigned `workspace_admin_id` to delete insurer master records belonging to their workspace.
     - In `db.delete_insurer_master(insurer_id, workspace_admin_id)`, ensure the SQL query strictly enforces workspace isolation: `DELETE FROM insurer_master WHERE id = %s AND workspace_admin_id = %s RETURNING id;`.
  3. **UI Feedback & Live Refresh (`static/script.js`):**
     - Update `deleteInsurerMaster(id)` in `static/script.js` to display clear status notifications (`showStatus`) on success or permission failure, and immediately reload the insurer master list (`loadInsurerMasters()`) so the deleted row disappears cleanly from the modal table and datalists.
- **Ambiguities & Trade-Offs:**
  - Workspace employees can delete master records they or their workspace admin created in their workspace. Cross-workspace deletion remains strictly blocked (`403/404`).
- **Risk Rating:** Low
- **App Area:** `Admin settings` / `Survey Fee Register` (Insurer Master Control Panel)

---

### R3: Claim Register — Fix Claim Creation, Persistence & Workspace-Wide Shared Visibility
- **Source:**
  - `WhatsApp Video 2026-08-21 at 8.42.44 AM.mp4` (0:00 – 0:28)
- **Exact Quote / Transcript (Hindi):**
  > *"Me new claim registration kar raha hu... sari cheez bhara hu... create kar raha hu... hat gaya... save nahi hua... Dashboard me New claim show hona chahiye... yahan par show nahi ho raha hai. Isko ek bar dekh lijiye."*
- **Interpretation & Functional Requirement:**
  1. **Context / Problem:**
     - In `static/script.js` (`createClaim`), the form submit handler only collected a partial subset of fields (omitting insured mobile/email, claim manager contact info, vehicle type, branch, and workshop details).
     - In `db.py` (`get_workspace_reports_page`), when `role == 'employee'`, an overly restrictive filter `(user_id = %s OR created_by = %s)` was applied, hiding workspace claims and showing "No claims found" even when claims exist in the workspace.
     - In `save_workspace_report`, `created_by` was not populated, causing new claims to disappear for employee accounts.
  2. **Complete Field Capture (`static/script.js`):**
     - Capture all `#new-claim-form` inputs: `claim_no`, `insured_name`, `insured_contact_no`, `insured_email`, `claim_manager_email`, `claim_manager_phone`, `vehicle_no`, `vehicle_type`, `policy_no`, `insurer`, `insurer_branch`, `workshop_name`, `workshop_phone`, `date_of_loss`, `survey_type`, `status`.
  3. **Workspace Sharing & Persistence (`app.py` & `db.py`):**
     - Ensure `POST /api/claims` safely accepts all fields, generates clean report numbers (e.g. `NIA/2026/01`), populates `user_id`, `created_by`, `workspace_admin_id`, `saved_at`, and `status = 'new_appointment'`.
     - In `db.get_workspace_reports_page` and `db.get_workspace_dashboard`, ensure all records in the active `workspace_admin_id` are returned for workspace members, while respecting the optional user filter dropdown ("All Team Members").
     - Upon creation, the new claim must immediately appear in the Claim Register table, and the Dashboard KPI card counters (`New appointment` and `Total claims`) must increment accordingly.
- **Ambiguities & Trade-Offs:**
  - Date inputs must accept both ISO format (`YYYY-MM-DD`) and standard Indian date format (`DD/MM/YYYY`) safely without parsing crashes.
- **Risk Rating:** Medium
- **App Area:** `Claim Register` / `Dashboard`

---

### R4: Claim Register — Intimation & Appointment PDF Upload / Instant Auto-Fill
- **Source:**
  - `WhatsApp Video 2026-08-21 at 8.42.44 AM.mp4` (0:30 – 2:25)
- **Exact Quote / Transcript (Hindi):**
  > *"Mera side se ek galti hua aapko bolne ka... Jab new claim kar rahe hai na, yahan par wo aapka PDF upload karenge... to us PDF me jo jo information milega wo information fill up kar lega... Gmail me jo appointment mail aata hai... insurance company se mujhe PDF de deta hai... is details ko agar upload karunga to jo jo information chahiye wo le lega."*
- **Interpretation & Functional Requirement:**
  1. **Context / Problem:** Surveyors regularly receive surveyor appointment letters and claim intimation emails (printed to PDF or received as attachments like `DocScanner...pdf` from National Insurance, New India, etc.). Typing each claim manually into the New Claim form is tedious and prone to typos. The client requests a direct PDF upload feature in the Claim Register that automatically extracts the intimation details and pre-fills the New Claim form.
  2. **UI & Dropzone in Claim Register (`#claim-register-section`):**
     - Add an **"Upload Appointment / Intimation PDF"** card with file browse button & drag-and-drop zone right above/inside the New Claim panel.
     - Support uploading appointment letters, Gmail intimation PDFs, and insurance claim intimations.
  3. **Backend Extraction Route (`POST /api/claims/extract_intimation`):**
     - Accepts uploaded PDF file, stores temporarily in private asset storage (`modules/assets.py`), and executes a targeted Gemini extraction prompt specialized for appointment letters & intimation PDFs.
     - Extracted JSON schema:
       ```json
       {
         "claim_no": "...",
         "policy_no": "...",
         "insured_name": "...",
         "insured_contact_no": "...",
         "insured_email": "...",
         "claim_manager_email": "...",
         "claim_manager_phone": "...",
         "vehicle_no": "...",
         "vehicle_type": "...",
         "insurer": "...",
         "insurer_branch": "...",
         "workshop_name": "...",
         "workshop_phone": "...",
         "date_of_loss": "...",
         "survey_type": "spot | final"
       }
       ```
  4. **Frontend Form Auto-Population:**
     - Automatically open `#new-claim-form`, populate all extracted fields into the inputs, trigger matching of Insurer Masters (auto-filling branch/GSTIN if configured), and display a success notification: *"Intimation data extracted successfully! Please review and click Create Claim."*
- **Ambiguities & Trade-Offs:**
  - Processing is lightweight and completes in seconds; can be handled with synchronous short timeout or queue with instant SSE/polling feedback.
- **Risk Rating:** Medium
- **App Area:** `Claim Register`

---

### R5: Background Worker & AI Extraction — Robust Gemini API Key Multi-Tenant Fallback & Error Diagnostics
- **Source:**
  - `WhatsApp Image 2026-08-21 at 4.36.24 PM.jpeg`
  - `Screenshot 2026-08-21 211510.png` (4:36 PM photo)
- **Exact Quote / Transcript:**
  > *"Error processing PDF: The background task could not be completed: 400 INVALID_ARGUMENT. {'error': {'code': 400, 'message': 'API key not valid. Please pass a valid API key.', 'status': 'INVALID_ARGUMENT', ...}}"*
- **Interpretation & Functional Requirement:**
  1. **Context / Problem:** When employee `USER` uploads a document for AI parsing, `worker.py` attempts to read the employee's `encrypted_gemini_api_key`. If the employee has an invalid or empty key override stored in their user profile, the worker passes the invalid key to Google GenAI and crashes with a `400 INVALID_ARGUMENT (API_KEY_INVALID)` error, dumping raw JSON dictionary text on screen.
  2. **Multi-Tenant Key Resolution Hierarchy (`modules/credentials.py` & `worker.py`):**
     - When resolving the Gemini API key for any job:
       1. Check requesting user's own encrypted key (if configured and non-empty).
       2. If empty or user is an employee, look up their workspace admin's (`SKANOWAR`) encrypted key.
       3. If still empty, fallback to the server environment's `GEMINI_API_KEY`.
  3. **Graceful Failover & Clean Error Messages (`modules/gemini.py` & `worker.py`):**
     - In `modules/gemini.py`, catch `API_KEY_INVALID` / 400 / 403 errors and attempt fallback to the system environment key before failing the job.
     - If all keys fail, return a sanitized, human-friendly error message:
       `"Gemini API key is invalid or not configured. Please verify your API key in Settings or contact your administrator."`
       rather than displaying raw Python dictionary tracebacks.
- **Ambiguities & Trade-Offs:**
  - Workspace admin keys take precedence for employees so that individual staff members do not need separate Google AI Studio API billing accounts.
- **Risk Rating:** Low
- **App Area:** `Reports` / `Admin settings` / `worker.py` / `modules/gemini.py`

---

## 3. Requirements vs Architecture Matrix

| Requirement | App Area | Files / Routes Affected | DB / Migration Needed | Risk |
|---|---|---|---|---|
| **R1: Restore Fee Register Edit Button** | `Survey Fee Register` | `static/script.js`, `templates/index.html` | No | Low |
| **R2: Fix Insurer Master Deletion** | `Admin settings`, `Survey Fee Register` | `app.py` (`DELETE /api/insurers/<id>`), `db.py`, `static/script.js` | No (SQL query update) | Low |
| **R3: Fix Claim Creation & Shared Visibility** | `Claim Register`, `Dashboard` | `app.py` (`/api/claims`), `db.py` (`save_workspace_report`, `get_workspace_reports_page`), `static/script.js` | No | Medium |
| **R4: Claim Intimation PDF Upload & Auto-Fill** | `Claim Register` | `templates/index.html`, `static/script.js`, `app.py` (`/api/claims/extract_intimation`), `modules/gemini.py` | No | Medium |
| **R5: Multi-Tenant Gemini Key Fallback & Diagnostics** | `Reports`, `worker.py`, `Admin settings` | `modules/credentials.py`, `worker.py`, `modules/gemini.py`, `app.py` | No | Low |

---

## 4. Acceptance Criteria Summary

- [ ] **AC1 (R1 - Fee Edit):** Clicking "Edit" on any Fee Register table row loads all invoice, insurer, claim, and 8-item breakdown details into `#fee-register-form` and updates the existing bill upon save without creating duplicate records.
- [ ] **AC2 (R2 - Insurer Delete):** Deleting an Insurer Master record from `#insurer-master-modal` as either Admin or Employee in the active workspace removes the record from the database and immediately updates the modal table.
- [ ] **AC3 (R3 - Claim Persistence):** Submitting a New Claim from `#new-claim-form` saves all fields, reserves a sequential report number, displays the claim in Claim Register for all workspace team members, and updates Dashboard KPI counters.
- [ ] **AC4 (R4 - Intimation PDF Upload):** Uploading an insurer appointment letter or intimation PDF in Claim Register extracts all claim metadata via AI and auto-fills `#new-claim-form` fields instantly.
- [ ] **AC5 (R5 - Gemini Key Fallback):** Employee document uploads inherit the workspace admin's Gemini API key and fallback gracefully to server environment keys, with clean error handling if keys are invalid.

---

🛑 **STOP POINT — Awaiting user approval on Phase 1 requirements before proceeding to Phase 2 (Implementation Plan).**