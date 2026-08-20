# Requirements Document — Client Changes Request (2026-08-20)

**Project:** Motor Survey Report Generator ([https://skinsurance.tech](https://skinsurance.tech))  
**Target Client:** Sk Anowar Ali (Surveyor & Loss Assessor)  
**Date:** 20 August 2026  
**Status:** Awaiting User Approval (PHASE 1 STOP POINT)

---

## Executive Summary & Media Ingestion Log

All client communications, audio voice notes, screen recordings, and chat threads from `Downloads/client changes request/` and WhatsApp chat history have been ingested and analyzed end-to-end natively:

| # | Media File | Type | Duration / Size | Sender | Summary / Core Issue |
|---|---|---|---|---|---|
| 1 | `WhatsApp Ptt 2026-08-20 at 12.38.47 AM.ogg` (`WhatsApp Ptt 2026-08-20 at 12.38.47 AM_audio.mp4`) | Audio (.ogg → native multimodal) | 01:11 / 168 KB | Sk Anowar Ali (Client) | Clarification on Dashboard counters: Total Claims = All files (Pending + Submitted/Closed). Pending Claims = Total active unsubmitted files. Sub-status counts (New appointment, Inspection pending, Documents awaited, Under preparation) are categorical subsets of Pending Claims and do not subtractively diminish Pending Claims. |
| 2 | `WhatsApp Video 2026-08-20 at 12.29.52 AM.mp4` | Video / Audio (.mp4) | 01:21 / 10.3 MB | Sk Anowar Ali (Client, logged in as `USER`) | (1) Navigation/Back button: Clicking "Back to Upload & Overview" jumps all the way back to Step 1 home page instead of returning to the previous view/workspace; (2) Claim Register: Status filter dropdown does not filter claims table properly. |
| 3 | `WhatsApp Video 2026-08-20 at 12.30.16 AM.mp4` | Video / Audio (.mp4) | 07:32 / 37.8 MB | Sk Anowar Ali (Client, logged in as `USER`) | (1) Dashboard should default to "Monthly Basis" with options for 3 Months, 6 Months, 1 Year, All Time, or Custom Range; (2) Dashboard drilldown shows "No claims found" when clicking non-zero KPI cards; (3) Missing Documents Checklist modal needs Insured Phone/Email inputs, Work Order vs Docs Pending template picker, message preview, and 7-day reminder indicator; (4) Survey Fee Register fixes: Insurer master access, policy PDF auto-fill, and reliable Save / Preview PDF without form validation blocks. |
| 4 | WhatsApp Chat History (`SK Anowar Ali Client`) | Text Messages | Recent messages | Client & Developer | Client confirmed: "Working, but we need change in the modification." Sent screen recordings and voice note at 12:29 AM - 12:38 AM. |

---

## Detailed Requirements Matrix (R1 – R6)

### R1: Dashboard Time-Period Filter & Default "Monthly Basis" View
- **Source:** `Downloads/client changes request/WhatsApp Video 2026-08-20 at 12.30.16 AM.mp4` (0:00 – 1:25) & `WhatsApp Ptt 2026-08-20 at 12.38.47 AM.ogg`
- **Exact Quote / Transcript (Hindi):**
  > *"Yeh jo Dashboard hai, yeh monthly basis claim ka status hai kya yearly basis hai, woh select option rehna chahiye. Yeh jo 116 file dikha rahe hain, iska matlab aapka isme up-to-date jitna saare file hai wahan par show kar rahe hain. Toh yeh jo Dashboard hai yeh monthly basis dikhayega... Jaise August mahina hai toh August mahine mein total kitna claim aaya... Generally default hona chahiye monthly basis."*
- **Interpretation:**
  1. **Default Timeframe:** The Dashboard metric bar must default to **"This Month" (Current Month, e.g. August 2026)** rather than lifetime data.
  2. **Time Range Dropdown:** Provide clean, intuitive dropdown options:
     - **This Month (Default)** — e.g. `2026-08-01` to current date.
     - **Last Month**
     - **Last 3 Months (Quarterly)**
     - **Last 6 Months (Half-Yearly)**
     - **This Financial Year / 1 Year**
     - **All Time (Lifetime)**
     - **Custom Date Range** (From Date / To Date).
  3. **Real-time Refresh:** Switching the timeframe immediately updates all operational metric cards, drill-down lists, and financial aggregates (for Admins).
- **Ambiguities & Trade-Offs:**
  - Date filtering should consider `COALESCE(email_received_date, saved_at, created_at)` so newly synced or manually created claims match their respective month accurately.
- **Risk Rating:** Medium
- **App Area:** `Dashboard`

---

### R2: Dashboard Metric Mathematical Integrity & Drill-Down Claim Rendering
- **Source:** `Downloads/client changes request/WhatsApp Ptt 2026-08-20 at 12.38.47 AM.ogg` & `WhatsApp Video 2026-08-20 at 12.30.16 AM.mp4` (1:25 – 3:45)
- **Exact Quote / Transcript (Hindi):**
  > *"Neeche wala video mein ek correction karna hai... Total Claims se ghatega nahi. Total Claims jitna total file hai woh saare cheez wahan par show hoga. Jo claim ka calculation distribute hoga woh Pending Claims se... Jo file jab tak submit nahi hoga, tab tak Pending Claim mein show hoga total... Aur jo video mein file show nahi kar raha hai jab click kar rahe hain, isko aapko theek karna padega."*
- **Interpretation:**
  1. **Mathematical Consistency:**
     - **`Total Claims`:** Overall claims in selected period $= \text{Pending Claims} + \text{Submitted Claims} + \text{Closed Claims}$.
     - **`Pending Claims`:** Total active, un-finalized claims (all claims whose status $\notin \{\text{'report\_submitted'}, \text{'closed'}\}$).
     - **Categorical Breakdown Cards:** *New appointment*, *Inspection pending*, *Documents awaited*, *Report under preparation* represent active subsets of Pending Claims. Their sum $\le \text{Pending Claims}$.
     - **`Submitted` / `Completed`:** Claims with final report drafted and bill generated.
     - **`Closed`:** Claims where fee remittance / payment is marked as received.
  2. **In-Place Drilldown Fix:** When clicking any metric card (e.g. *Inspection pending*, *Documents awaited*, *New appointment*), the drilldown table (`#dashboard-drilldown-section`) must fetch and render the exact matching claims in the active time range, eliminating the "No claims found for Inspection pending (0)" bug observed in Video 2.
  3. **Direct Navigation:** Add "Open Report" and "Docs" quick actions directly on each drilldown row.
- **Ambiguities & Trade-Offs:**
  - Standardize status keys between backend SQL queries and frontend JavaScript filters (`new_appointment`, `inspection_pending`, `documents_awaited`, `report_under_preparation`, `report_submitted`, `closed`) to guarantee 1:1 parity.
- **Risk Rating:** Medium
- **App Area:** `Dashboard` / `Claim Register`

---

### R3: Claim Register Status Filter & Search Fix
- **Source:** `Downloads/client changes request/WhatsApp Video 2026-08-20 at 12.29.52 AM.mp4` (0:45 – 1:21)
- **Exact Quote / Transcript (Hindi):**
  > *"Yeh status mein yeh kaam nahi kar raha hai aapka... documents awaited kiya dekhiye documents awaited file nahi aa raha hai... yeh kaam nahi kar raha hai, isko aapko thoda dekhna padega."*
- **Interpretation:**
  1. Fix the `#claim-status-filter` dropdown in the Claim Register so selecting `Documents awaited`, `Inspection pending`, `New appointment`, `Report under preparation`, or `Report submitted` correctly queries `/api/claims?status=...` and updates `#claim-register-tbody`.
  2. Ensure combined filters (Search text + Status dropdown + Month filter + User filter) work together cleanly without resetting pagination to invalid pages.
  3. Ensure status changes made via dropdown in the Claim Register table immediately update the status on the server and synchronize the Dashboard counters.
- **Ambiguities & Trade-Offs:**
  - Status names in the filter dropdown must strictly match the database canonical values (`new_appointment`, `inspection_pending`, `documents_awaited`, `report_under_preparation`, `report_submitted`, `closed`) while displaying formatted titles to the user.
- **Risk Rating:** Low
- **App Area:** `Claim Register`

---

### R4: Contextual Navigation & Intuitive "Back" Routing
- **Source:** `Downloads/client changes request/WhatsApp Video 2026-08-20 at 12.29.52 AM.mp4` (0:00 – 0:45)
- **Exact Quote / Transcript (Hindi):**
  > *"Idhar na aapko ek back karne ka option rehna padega... iske pehle jo step mein tha, us step mein jab back karke aaunga woh nahi hoga. Yeh dekhiye back karunga toh pura ekdam homepage mein chala jayega... isme dikkat hai."*
- **Interpretation:**
  1. Replace the generic "Back to Upload & Documents" button with a contextual navigation hierarchy:
     - When inside **Survey Fee Register**, clicking "Back" returns to the previous view (e.g. **Claim Register** or **Dashboard**).
     - When viewing a **Claim / Report Form**, provide a clear "Back to Claim Register" / "Back to Dashboard" button that returns to the operational list without losing filters or state.
     - When on the **Dashboard** or **Claim Register**, provide a clear "Back to Home / Upload" button.
  2. Ensure the top navigation bar (`#workspace-active-nav`) clearly reflects the active tab (Dashboard, Claim Register, Fee Register) with smooth tab switching that never abruptly forces the user to the file upload dropzone.
- **Ambiguities & Trade-Offs:**
  - Use a view history stack (`workspaceState.previousView`) in JavaScript to seamlessly return to whichever view the user came from.
- **Risk Rating:** Low
- **App Area:** `Dashboard` / `Claim Register` / `Survey Fee Register` / `Reports`

---

### R5: Missing Documents Checklist Modal Enhancements & Template Notification Picker
- **Source:** `Downloads/client changes request/WhatsApp Video 2026-08-20 at 12.30.16 AM.mp4` (3:50 – 5:05)
- **Exact Quote / Transcript (Hindi):**
  > *"Claim Register mein... Docs mein... yeh bilkul theek hai. Yahan par Claim Manager Mail aur Claim Manager Phone... Yahan par customer ko bhi phone aur mail chahiye. Aur notification mein jo send karunga, woh kahan par show karega dikha dijiyega... Ek option rahega: Work Order ya Documents Pending... Aur ek hafta baad mujhe blink karega ki iska documents pending hai ek hafta se."*
- **Interpretation:**
  1. **Customer / Insured Contact Fields:** Add inputs for **Insured Mobile No.** (`insured_contact_no`) and **Insured Email ID** (`insured_email`) in the Missing Documents Checklist Modal alongside Claim Manager contacts, pre-filled from claim data.
  2. **Notification Template Selector:**
     - **Template A: "Work Order / Inspection Intimation"** (Formal intimation acknowledging survey appointment and requesting garage/vehicle inspection access).
     - **Template B: "Documents Pending Reminder"** (Itemized checklist of pending documents with 1st, 2nd, and 3rd notice escalation wording).
  3. **Live Message Preview Box:** Display a read-only live text preview box inside the modal showing the exact generated message before sending or copying.
  4. **WhatsApp & Copy Actions:** Generate both one-click WhatsApp web links and clipboard copy buttons for Claim Manager and Insured contacts.
  5. **7-Day Document Pending Aging Flag:**
     - In Claim Register and Dashboard, add a visual badge / pulse indicator for claims where documents have been pending for $\ge 7$ days without completion.
     - Ticking off all documents or updating status clears the indicator.
- **Ambiguities & Trade-Offs:**
  - Retain the existing automated 3-tier reminder counter (Reminder 1, Reminder 2 Final, Reminder 3 Critical notice) while supporting the Work Order template option.
- **Risk Rating:** Medium
- **App Area:** `Claim Register` / `Dashboard` / `Admin settings`

---

### R6: Survey Fee Register Reliability, Insurer Master Access & PDF Auto-Extraction
- **Source:** `Downloads/client changes request/WhatsApp Video 2026-08-20 at 12.30.16 AM.mp4` (5:05 – 7:32)
- **Exact Quote / Transcript (Hindi):**
  > *"Yeh jo Master hai yahan par kaam nahi kar raha hai... Aur yahan par upload kiya jo policy copy, upload karne se insurer name, address, GST le lega... Lekin yeh kaam nahi kar raha hai... Itemized breakdown sahi karke diya hai, main yehi cheez chahta tha... Lekin Save Fee Bill aur Download Preview PDF nahi ho raha hai, 'Please fill out this field' aa raha hai... isko theek karna padega."*
- **Interpretation:**
  1. **Insurer Master Modal Access for Employees:** Ensure employee users (`USER`) can open `#insurer-master-modal`, create/edit insurer masters, and select branch GSTINs without permission blocks.
  2. **Policy / RC Copy PDF Auto-Extraction:** Fix `/api/extract_fee_pdf` so uploading a Policy/RC PDF in Fee Register automatically extracts and pre-fills Insurer Name, Insurer GSTIN, Branch Address, Policy No, Claim No, Vehicle Regn No, and Insured Name.
  3. **Itemized Fee Saving & PDF Preview:**
     - Fix form validation so hidden/optional inputs do not trigger browser `Please fill out this field` validation errors.
     - Ensure `/api/fee_bills` POST and `/generate_fee_pdf` handle all 8 itemized fee rows (Final Survey Fees, Conveyance with route & KM formula, 2nd visit Conveyance, Re-inspection, Photos, Halting, Other charges) seamlessly for both standalone and linked claims.
     - Ensure newly saved fee bills immediately appear in the Fee Register table and are downloadable via `/api/fee_bills/<id>/pdf`.
- **Ambiguities & Trade-Offs:**
  - Standalone fee bills should cleanly set `report_id = NULL` rather than empty strings to prevent PostgreSQL integer cast errors.
- **Risk Rating:** High (Core client invoicing and fee recovery pipeline).
- **App Area:** `Survey Fee Register` / `Reports` / `Admin settings`

---

## App Area to Requirements Mapping

| App Area | Touching Requirements | Key Files / Seams |
|---|---|---|
| **Dashboard** | **R1, R2, R4, R5** | `templates/index.html`, `static/script.js`, `app.py`, `db.py` |
| **Claim Register** | **R2, R3, R4, R5** | `templates/index.html`, `static/script.js`, `app.py`, `db.py` |
| **Survey Fee Register** | **R4, R6** | `templates/index.html`, `static/script.js`, `app.py`, `db.py`, `modules/pdf.py` |
| **Reports** | **R4, R6** | `templates/index.html`, `static/script.js`, `modules/pdf.py`, `worker.py` |
| **Admin Settings** | **R5, R6** | `templates/index.html`, `static/script.js`, `app.py` |
| **Exports** | **R1, R6** | `app.py` (`/export_gstr1_excel`, `/api/admin/backup/download`) |
| **Gmail Sync** | **R1, R2** | `modules/gmail.py`, `worker.py` |

---

## Verification & Acceptance Criteria

- [ ] **AC1 (Dashboard Time Filter):** Dashboard defaults to "This Month" (August 2026) and accurately recalculates metrics when switching to Last 3 Months, 6 Months, 1 Year, All Time, or Custom Date Range.
- [ ] **AC2 (Dashboard Drilldown):** Clicking any KPI card (*Inspection pending*, *Documents awaited*, *New appointment*, *Report under preparation*, *Submitted*, *Closed*) displays matching claims in `#dashboard-drilldown-section` with no "No claims found" errors when counts are $>0$.
- [ ] **AC3 (Claim Register Filters):** Status filter dropdown in Claim Register accurately filters table by `Documents awaited`, `Inspection pending`, `New appointment`, `Report under preparation`, and `Report submitted`.
- [ ] **AC4 (Contextual Navigation):** Clicking "Back" inside any sub-section returns to the previously active view rather than abruptly jumping to the Step 1 file dropzone.
- [ ] **AC5 (Docs Checklist & Notifications):** Missing Documents modal includes Insured contact fields, Work Order vs Docs Pending template picker, live message preview, and 7-day reminder aging indicator.
- [ ] **AC6 (Survey Fee Register Save & PDF):** Policy PDF upload auto-fills billing details; Insurer Master modal opens smoothly for employees; and all 8 itemized fee rows save and generate Word-template style PDF fee bills reliably without validation errors.
- [ ] **AC7 (Security & Invariants):** Employee role cannot view corporate financial aggregates or tax exports (`403 Forbidden`). All pytest tests pass.

---
**STOP POINT:** Awaiting user approval on `requirements2026-08-20.md` before proceeding to PHASE 2 (Plan) and PHASE 3 (Implementation).
