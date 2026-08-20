# Requirements Document — Client Changes Request (2026-08-20)

**Project:** Motor Survey Report Generator ([https://skinsurance.tech](https://skinsurance.tech))  
**Target Client:** Sk Anowar Ali (Surveyor & Loss Assessor)  
**Date:** 20 August 2026 (Night Session — 21:25 IST)  
**Status:** 🛑 **STOP POINT — Awaiting User Approval (PHASE 1)**

---

## 1. Executive Summary & Media Ingestion Log (Phase 0)

All media files located in `Downloads/client changes request/` have been listed, converted where necessary, and ingested natively end-to-end via multimodal analysis. Zero policyholder PII has been transmitted to external services.

### Complete Media Files Ingestion Table

| # | File Name | Type | Size / Duration | Sender | Core Subject / Evidence Captured |
|---|---|---|---|---|---|
| 1 | `WhatsApp Image 2026-08-20 at 9.09.20 PM.jpeg` | Image (.jpeg) | 87.7 KB | Sk Anowar Ali (Client) | Photo of physical survey fee bill showing: `HSN/SAC-997162`, `Insurer's Surveyor Code No: 2075995`, `GSTIN: 19AZZPA2301R1ZM`, SBI Bank details. Caption: *"Surveyor code"*. |
| 2 | `WhatsApp Image 2026-08-20 at 9.09.42 PM.jpeg` | Image (.jpeg) | 99.5 KB | Sk Anowar Ali (Client) | Photo of current web application screen showing the **Insurer Master Control Panel** modal with input fields for Insurer Name, Branch, Prefix, GSTIN, State Code, Rate/Km, and Address. |
| 3 | `Screenshot 2026-08-20 212259.png` | Image (.png) | 630.8 KB | Naman / Sk Anowar Ali | Full chronological chat thread from 9:09 PM to 9:16 PM showing message *"Surveyor code option create karna hai"* (9:10 PM), voice notes, and fee register screenshot. |
| 4 | `WhatsApp Ptt 2026-08-20 at 9.11.07 PM.ogg` (`vn1.mp4`) | Audio (.ogg → native multimodal) | 66.7 KB / 00:29 | Sk Anowar Ali (Client) | Voice note requesting: (1) Insurer-specific Surveyor Code option in Insurer Master Control Panel so different insurer surveyor codes can be saved and auto-populated; (2) Fee Bill Preview currently forces a PDF file download instead of previewing in-browser. |
| 5 | `WhatsApp Image 2026-08-20 at 9.13.45 PM.jpeg` | Image (.jpeg) | 122.0 KB | Sk Anowar Ali (Client, logged in as `USER`) | Photo of **Survey Fee Register** table with mouse cursor pointing directly at the `unpaid` status badge and the actions column next to the PDF download button. |
| 6 | `WhatsApp Ptt 2026-08-20 at 9.14.53 PM.ogg` (`vn2.mp4`) | Audio (.ogg → native multimodal) | 7.7 KB / 00:03 | Sk Anowar Ali (Client) | Short voice clip: *"Matlab PDF ke bagal me..."* (referencing placement of the payment action next to the PDF button in the Fee Register row). |
| 7 | `WhatsApp Ptt 2026-08-20 at 9.16.01 PM.ogg` (`vn3.mp4`) | Audio (.ogg → native multimodal) | 70.8 KB / 00:30 | Sk Anowar Ali (Client) | Voice note detailing payment lifecycle: fee bills are submitted as `unpaid`, insurers pay 7–20 days later. When paid, user must be able to mark status as `paid` / update payment and enter **Remarks** because insurance companies frequently make short payments / deductions. |

---

## 2. Requirements Specification (R1 – R3)

### R1: Insurer Master — Insurer-Specific Surveyor Code Field & Dynamic Prefill / PDF Rendering
- **Source:**
  - `WhatsApp Image 2026-08-20 at 9.09.20 PM.jpeg`
  - `WhatsApp Image 2026-08-20 at 9.09.42 PM.jpeg`
  - `Screenshot 2026-08-20 212259.png` (9:10 PM message: *"Surveyor code option create karna hai"*)
  - `WhatsApp Ptt 2026-08-20 at 9.11.07 PM.ogg` / `vn1.mp4` (0:00 – 0:19)
- **Exact Quote / Transcript (Hindi):**
  > *"Surveyor jo code hai, wo code wo jo master control panel me wo option aapko daalna padega. Kyunki surveyor code wo saare jagah me ek hi le raha hai. To wo code option daalna padega, jab mai master control panel me add karunga to wo surveyor code daal dunga to usi hisab se wo le lega."*
- **Interpretation & Functional Requirement:**
  1. **Context / Problem:** In motor survey operations, insurance companies assign distinct Surveyor Code numbers (e.g. National Insurance has one surveyor ID, United India Insurance has surveyor code `2075995`, Oriental Insurance has another). Currently, the codebase hardcodes/defaults surveyor code universally to `'2075995'` everywhere.
  2. **Database & API Schema (`insurer_master`):**
     - Add `surveyor_code VARCHAR(100)` column to table `insurer_master` in `migrations/0014_insurer_surveyor_code_and_fee_payments.sql`.
     - Update `get_insurer_masters()`, `get_insurer_master_by_id()`, and `save_insurer_master()` in `db.py` to persist and return `surveyor_code`.
  3. **UI / Insurer Master Control Panel Modal:**
     - Add an **"Insurer's Surveyor Code"** input field (`#im-surveyor-code`, placeholder e.g. `2075995`) in `#insurer-master-modal` in `templates/index.html`.
     - Add a "Surveyor Code" column to the configured insurer table inside the Insurer Master modal.
  4. **Dynamic Prefill in Fee Register & Claim Forms:**
     - When selecting an insurer in the Survey Fee Register or Claim form, dynamically pre-fill the Surveyor Code field with the insurer's specific `surveyor_code` (falling back to user profile surveyor code or `'2075995'` if blank).
  5. **Fee Bill PDF & Word Templates:**
     - Ensure the generated Fee Bill PDF (`modules/pdf.py`) and fee bill records print `Insurer's Surveyor Code No: <insurer_surveyor_code>` using the active insurer's surveyor code.
- **Ambiguities & Trade-Offs:**
  - If an existing insurer record has no surveyor code set, fallback smoothly to the surveyor profile's license/code or `'2075995'`.
- **Risk Rating:** Low
- **App Area:** `Survey Fee Register` / `Admin settings` (Insurer Master) / `Reports`

---

### R2: Survey Fee Register — In-Browser PDF Preview (Modal / New Tab) vs Direct Download
- **Source:**
  - `WhatsApp Ptt 2026-08-20 at 9.11.07 PM.ogg` / `vn1.mp4` (0:19 – 0:29)
- **Exact Quote / Transcript (Hindi):**
  > *"Aur dusra baat hai iska jo preview kar raha hu, to preview me preview nahi ho raha hai, wo direct ek PDF download ho ja raha hai. Theek hai? Ye cheez dekhna hai."*
- **Interpretation & Functional Requirement:**
  1. **Context / Problem:** In `static/script.js` (`handleDownloadFeePdfPreview()`), clicking "Download Preview PDF" generates the PDF blob and immediately triggers a synthetic `<a download="FeeBill.pdf">` download click. This fills the client's local Downloads folder with temporary drafts whenever they only want to inspect the generated bill layout.
  2. **In-Browser Preview:**
     - Update the "Preview Fee Bill" action so that clicking it opens an **in-browser PDF preview** inside the application's preview modal (`#preview-modal` / `#preview-iframe` or `window.open(previewUrl, '_blank')`).
     - Allow the surveyor to review the bill layout, itemized charges, GST breakdown, bank details, and surveyor code directly on screen without forcing a file download.
     - Keep a clear "Download PDF" button in the preview header or fee register table for when the user explicitly intends to save the file to disk.
- **Ambiguities & Trade-Offs:**
  - PDF generation uses `/generate_fee_pdf` or ephemeral asset token via `modules/assets.py` to ensure multi-worker Gunicorn consistency without saving public files under `/static`.
- **Risk Rating:** Low
- **App Area:** `Survey Fee Register`

---

### R3: Survey Fee Register — Fee Bill Payment Lifecycle (Mark Paid, Payment Date, Amount Received, TDS & Short-Payment Remarks)
- **Source:**
  - `WhatsApp Image 2026-08-20 at 9.13.45 PM.jpeg`
  - `WhatsApp Ptt 2026-08-20 at 9.14.53 PM.ogg` / `vn2.mp4` (*"Matlab PDF ke bagal me..."*)
  - `WhatsApp Ptt 2026-08-20 at 9.16.01 PM.ogg` / `vn3.mp4` (0:00 – 0:30)
- **Exact Quote / Transcript (Hindi):**
  > *"Insurance... Insurance wale ko mai survey report bana kar fees ek karta hu, fees charge karta hu aur usko jama karta hu. Wo humko 20 din, 15 din, ek hafta baad payment karta hai. Wo jab payment karega tab hum isko 'paid' kar denge, jo abhi mera status me 'unpaid' hai. To tab mai payment 'paid' karunga to wo kaise karunga thoda aap usko ek arrange kijiye. Aur remark ka option rakhiyega kyunki insurance wala sometime wo short payment karta hai, to wo remark humko rakhna hai."*
- **Interpretation & Functional Requirement:**
  1. **Context / Problem:** When survey reports and fee bills are created, they are submitted to insurance companies with status `unpaid`. Insurers remit survey fees 1 to 3 weeks later. Insurers frequently disallow specific line items (e.g. conveyance excess) or deduct statutory TDS, resulting in short-payments. The surveyor requires a streamlined way to mark bills as `paid` or `partially_paid`, log the payment date and received amount, and record a **Payment Remark** explaining short-payments or deductions.
  2. **Database & API Schema (`fee_bills`):**
     - Ensure table `fee_bills` has columns: `payment_status VARCHAR(50) DEFAULT 'unpaid'`, `amount_received NUMERIC(12,2) DEFAULT 0`, `tds_amount NUMERIC(12,2) DEFAULT 0`, `payment_date DATE`, `payment_reference VARCHAR(100)`, and `payment_remarks TEXT` (in migration `migrations/0014_insurer_surveyor_code_and_fee_payments.sql`).
     - Create endpoint `POST /api/fee_bills/<bill_id>/payment` (and update `PUT/POST /api/fee_bills`) with workspace scoping (`workspace_admin_id`), audit logging, and employee authorization.
  3. **UI / Fee Register Table & Modal:**
     - In `fetchFees()` table rendering (`#fee-register-tbody`):
       - Next to the PDF button in each row, add a **"Payment" / "Update Status"** button (e.g. `<button class="btn btn-sm btn-outline-success update-fee-payment-btn" data-bill-id="...">💳 Payment</button>`).
       - Status badge styling:
         - `paid`: Green badge (`badge-success` / `bg-emerald-500`)
         - `partially_paid`: Amber badge (`badge-warning` / `bg-amber-500`)
         - `unpaid`: Gray badge (`badge-outline` / `badge-secondary`)
       - If payment remarks exist, show a small info icon or tooltip on the row displaying the short-payment note.
     - **Payment Update Modal (`#fee-payment-modal`):**
       - Modal displays Bill Invoice No, Insurer, Claim No, and Total Bill Amount (₹).
       - Inputs:
         - **Payment Status Dropdown:** `Paid`, `Partially Paid`, `Unpaid`
         - **Payment Received Date:** Date picker (defaults to today)
         - **Amount Received (₹):** Number input (auto-fills Total Amount when selecting `Paid`)
         - **TDS Amount (₹):** Number input (optional)
         - **Payment Remarks / Short-Payment Reason:** Multi-line textarea (e.g. *"Deducted Rs. 325 for conveyance slab; TDS 10% deducted"*).
       - Save Button: Submits via AJAX, instantly refreshes the fee register list and dashboard KPI counters.
  4. **RBAC & Financial Security:**
     - Both Admin (`SKANOWAR`) and Employee (`USER`) accounts in the workspace can update the payment status and remarks of operational fee bills.
     - Corporate high-level financial turnover and tax exports remain strictly redacted and restricted to Admin accounts.
- **Ambiguities & Trade-Offs:**
  - Changing status to `Paid` should also update the linked dashboard status and claim fee settlement status where appropriate.
- **Risk Rating:** Medium
- **App Area:** `Survey Fee Register` / `Dashboard`

---

## 3. Requirements Mapping Matrix

| Requirement | App Area | Primary Files Impacted | Migration Required | RBAC Scope |
|---|---|---|---|---|
| **R1: Insurer Surveyor Code** | `Survey Fee Register`, `Admin settings`, `Reports` | `db.py`, `app.py`, `templates/index.html`, `static/script.js`, `modules/pdf.py` | Yes (`insurer_master.surveyor_code`) | Shared in Workspace |
| **R2: In-Browser PDF Preview** | `Survey Fee Register` | `static/script.js`, `templates/index.html`, `app.py` | No | Admin & Employee |
| **R3: Payment Status & Remarks** | `Survey Fee Register`, `Dashboard` | `db.py`, `app.py`, `templates/index.html`, `static/script.js` | Yes (`fee_bills.payment_date`, `payment_remarks`, etc.) | Admin & Employee |

---

## 4. Architectural Invariants & Compliance Verification

| Invariant | System Rule | Status |
|---|---|---|
| **Workspace Isolation** | All `insurer_master` and `fee_bills` queries filtered by `workspace_admin_id`. | ✅ Strictly Enforced |
| **No ORM** | Raw parameterized SQL with `psycopg2` only. | ✅ Strictly Enforced |
| **Private Assets** | Ephemeral previews routed through `modules/assets.py` and memory blobs. | ✅ Strictly Enforced |
| **RBAC Redaction** | Employee saves cannot overwrite admin financial summaries; tax exports remain admin-only. | ✅ Strictly Enforced |
| **Audit Logging** | All payment status changes and insurer master modifications log to `audit_logs`. | ✅ Strictly Enforced |
| **Idempotent Migrations** | `migrations/0014_insurer_surveyor_code_and_fee_payments.sql` uses `IF NOT EXISTS` / `ADD COLUMN IF NOT EXISTS`. | ✅ Strictly Enforced |

---

🛑 **STOP POINT — Phase 1 Complete.**  
Please review and confirm approval of requirements **R1, R2, and R3** before we proceed to Phase 2 (Implementation Plan) and Phase 3 (Feature Branch Implementation).
