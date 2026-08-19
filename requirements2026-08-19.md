# Requirements Document — Client Changes Request (2026-08-19)

**Project:** Motor Survey Report Generator ([https://skinsurance.tech](https://skinsurance.tech))  
**Target Client:** Sk Anowar Ali (Surveyor & Loss Assessor)  
**Date:** 19 August 2026  
**Status:** Awaiting User Approval (PHASE 1 STOP POINT)

---

## Executive Summary & Media Ingestion Log

All client communications, audio voice notes, screen recordings, and chat threads from `downloads/client changes request/` and WhatsApp chat history have been ingested and analyzed end-to-end:

| # | Media File | Type | Duration / Size | Sender | Summary / Core Issue |
|---|---|---|---|---|---|
| 1 | `WhatsApp Video 2026-08-19 at 8.23.53 AM.mp4` | Video / Audio (.mp4) | 0:54 / 4.26 MB | Sk Anowar Ali (Client, logged in as `USER`) | Employee cannot open `+ Masters` modal in Survey Fee Register; Client requests saving multiple branch addresses & multiple GSTINs per insurance company. |
| 2 | `WhatsApp Ptt 2026-08-19 at 9.40.53 AM.ogg` (`voice_note_1.mp4`) | Audio (.ogg → .mp4) | 0:18 / 38.8 KB | Sk Anowar Ali (Client) | Fee bills created for new insurers (Reliance / IndusInd) fail to save, do not download PDF, and do not appear in Fee Register table. |
| 3 | `WhatsApp Ptt 2026-08-19 at 3.47.07 PM.ogg` (`voice_note_2.mp4`) | Audio (.ogg → .mp4) | 0:23 / 53.2 KB | Sk Anowar Ali (Client) | User isolation concern: Admin and employee files are mixing together; also asks to verify that the fee entry section inside the final survey report generator is intact. |
| 4 | WhatsApp Chat (`SK Anowar Ali Client`) | Text Messages | 50+ messages | Client & Developer | Client requests urgent fee section fixes ("fees section show nahi karraha hai", "Time mile too fixed kardijega"). |
| 5 | `WhatsApp Video 2026-08-07 at 5.20.03 PM.mp4` | Video / Audio (.mp4) | 0:26 / 5.83 MB | Staff / Client | Shows "Error generating preview: The background task could not be completed" on PDF generation and displays report fee section. |

---

## Detailed Requirements Matrix (R1 – R6)

### R1: Insurer Master Multi-Branch & Multi-GSTIN Support + Employee Access
- **Source:** `downloads/client changes request/WhatsApp Video 2026-08-19 at 8.23.53 AM.mp4` (0:00 – 0:54)
- **Exact Quote / Transcript (Hindi):**
  > *"Number 1: Master kaam nahi kar raha hai... yahan par click kar raha hoon yeh kaam nahi kar raha hai... Idhar par toh Select ka option hai, Master mein add hoga toh Select mein aa jayega. Yeh Master kaam nahi kar raha hai... Add karenge jo insurance company ka name, uska address aur GST number jo karenge... Ek insurance company ka 2-3 address ho sakta hai, GST bhi 1-2 ho sakta hai... Toh aise isko cheese banana hai Master mein, jo ek insurance company ka address 1, address 2, address 3 mein save kar sakun, GST bhi 1, 2, 3 mein save kar sakun... yahan par Master mein."*
- **Interpretation:**
  1. **Fix Employee Access:** Fix `.open-insurer-master-modal-btn` and update `/api/insurers` so employee users (`USER`) can open the Insurer Master Modal, load saved master records, and save/update insurer details without receiving `403 Forbidden` errors.
  2. **Multi-Address & Multi-GSTIN Support:** Allow multiple branch offices, addresses, and GSTINs under the same insurance company name (e.g. National Insurance Company → Kolkata DO 1, Kolkata DO 2, Siliguri BO).
  3. **Auto-Population in Fee Register & Claim Register:** When typing or selecting an insurer name in Survey Fee Register or Claim Register, the system must provide datalists / select options for all saved branch addresses and GSTINs belonging to that insurer.
- **Ambiguities & Trade-Offs:**
  - *Data model choice:* Storing individual branch records with branch names/addresses while aggregating unique insurer names, branch addresses, and GSTINs into dynamic datalists in the frontend provides full backward compatibility and maximum usability.
- **Risk Rating:** Medium
- **App Area:** `Survey Fee Register` / `Admin settings`

---

### R2: Reliable Fee Bill Save, List Visibility & PDF Download for All Insurers
- **Source:** `downloads/client changes request/WhatsApp Ptt 2026-08-19 at 9.40.53 AM.ogg` (`voice_note_1.mp4`)
- **Exact Quote / Transcript (Hindi):**
  > *"Mai ek fees generate kiya... lekin wo save nahi ho raha hai... aur download bhi nahi ho raha hai. Aap do trial kiya Oriental ka, wo fees yahan par show kar rahe hain, lekin mai abhi ek Reliance ka kiya hoon... mane IndusInd ka hai... toh wo show nahi kar raha hai."*
- **Interpretation:**
  1. **Save Validation & Foreign Key Safety:** Ensure `/api/fee_bills` POST accepts both linked claims (`report_id`) and standalone bills (`report_id: null`) without transaction rollback.
  2. **Sequential Numbering for Employees:** Ensure `/api/insurers/next-invoice-no` allows employee accounts (`USER`) in the active workspace to fetch sequential invoice numbers (remove unnecessary `is_admin_user` block).
  3. **Query Filtering:** Ensure `get_workspace_fee_bills` filters properly by `workspace_admin_id` so newly saved fee bills for any insurer (Reliance, IndusInd, Oriental, National) immediately appear in the Fee Register table for all workspace members.
  4. **PDF Preview & Saved Download:** Ensure `/generate_fee_pdf` and `/api/fee_bills/<id>/pdf` generate clean, formatted Word-template style PDF fee bills with fallback to surveyor master details.
- **Ambiguities & Trade-Offs:**
  - When an unlinked fee bill is saved, make sure `report_id` is cleanly stored as `NULL` and not an empty string `""` to prevent PostgreSQL integer / foreign key casting errors.
- **Risk Rating:** High (Directly affects surveyor revenue invoicing and client workflow).
- **App Area:** `Survey Fee Register` / `Reports`

---

### R3: User File Segregation & Ownership Scoping ("Mera file uske paas chala ja raha hai")
- **Source:** `downloads/client changes request/WhatsApp Ptt 2026-08-19 at 3.47.07 PM.ogg` (`voice_note_2.mp4`) (0:00 – 0:13)
- **Exact Quote / Transcript (Hindi):**
  > *"Woh nahi mujhe phone kiya tha. Mera file uske paas chala ja raha hai. Iska ek baar dekhiye, dono ka divide divide rahega. Mera... mera jo user ID hoga mera files show karega, uska uska files show karega."*
- **Interpretation:**
  1. The client observed that reports and claims created by different accounts (`SKANOWAR` vs `USER`) appear shared across the workspace without a way to filter or keep individual files separate.
  2. **Segregation & Role Visibility:**
     - **Employee View (`USER`):** Show only the claims, reports, and draft files created by or assigned to that employee (`user_id = current_user.id`).
     - **Admin View (`SKANOWAR` / `NAMAN`):** Admin can view all workspace reports, but also has a quick filter toggle ("All Team Files" vs "My Files" vs specific employee).
     - **Claim Register & Saved Reports Table:** Display the creator / assigned user badge on each claim row.
- **Ambiguities & Trade-Offs:**
  - If an employee's access is restricted to only their own files, the Admin must still retain overall supervision to review and finalize employee reports. Therefore, employee queries will filter `user_id = current_user.id AND workspace_admin_id = admin_id`, while admin queries default to the entire workspace with a creator filter.
- **Risk Rating:** High (Core data scoping and RBAC architecture).
- **App Area:** `Claim Register` / `Dashboard` / `Reports`

---

### R4: Verify & Restore Survey Fee Entry in Survey Report Generator
- **Source:** `downloads/client changes request/WhatsApp Ptt 2026-08-19 at 3.47.07 PM.ogg` (`voice_note_2.mp4`) (0:13 – 0:23) & `WhatsApp Video 2026-08-07 at 5.20.03 PM.mp4`
- **Exact Quote / Transcript (Hindi):**
  > *"Aur jo report ke andar, jo final report jab banate hain hum log, uske andar ek fee put karne ka jagah hai, woh cheez shayad hat gaya hai."*
- **Interpretation:**
  1. Ensure that within the Motor Survey Report Generator (the main survey report editing form under Review & Edit), the "Page 3: Tax Invoice Details / Survey Fees & Payment Details" section remains fully visible, easily accessible, and prefilled with default professional fee values.
  2. Ensure that fee items entered in the report editor (Professional Fee, Conveyance, Photos, GST) correctly persist into `report_data_json`, calculate live totals, and render into the generated Final Survey Report PDF Bill page.
- **Ambiguities & Trade-Offs:**
  - Ensure clear UI distinction between: (a) The standalone **Survey Fee Register** (for standalone GST invoices) and (b) The **Survey Report Form Bill Section** (for survey reports containing an embedded fee bill page). Both must work seamlessly.
- **Risk Rating:** Medium
- **App Area:** `Reports`

---

### R5: Background Worker & PDF Generation Reliability
- **Source:** `downloads/client changes request/WhatsApp Video 2026-08-07 at 5.20.03 PM.mp4`
- **Exact Symptom:**
  > *"Error generating preview: The background task could not be completed. Please try again."*
- **Interpretation:**
  1. Ensure background PDF preview tasks (`modules/jobs.py`, `worker.py`) handle all report types, Nil Depreciation policies, towing calculations, and fee tables without crashing or timing out.
  2. Verify that ephemeral preview assets generated by `worker.py` are properly written to `modules/assets.py` private database storage so multi-worker Gunicorn web processes can stream the PDF immediately.
- **Ambiguities & Trade-Offs:**
  - Worker timeout configuration: Ensure `insurance-worker` systemd service has proper error handling and logging prefixes (`[JOB-FAILED]`, `[WORKER]`).
- **Risk Rating:** Medium
- **App Area:** `Reports` / `Dashboard`

---

### R6: Strict RBAC & Financial Redaction Security Invariant
- **Source:** `CONTEXT.md` Active Architectural Constraints & Binding Invariants
- **Requirement:**
  1. Financial summary cards (`#financial-dashboard`) and GSTR-1 / CA tax Excel exports (`/export_gstr1_excel`) must remain strictly hidden and blocked (`403 Forbidden`) for employee accounts.
  2. Employees can draft and view individual fee bills they create, but cannot delete fee bills or reports (`403 Forbidden`).
  3. All state-modifying requests require CSRF token validation and parameterized SQL queries only.
- **Ambiguities & Trade-Offs:** None. Binding architectural invariant.
- **Risk Rating:** Critical
- **App Area:** `Survey Fee Register` / `Dashboard` / `Exports` / `Admin settings`

---

## App Area to Requirements Mapping

| App Area | Touching Requirements | Key Files / Seams |
|---|---|---|
| **Survey Fee Register** | **R1, R2, R6** | `templates/index.html`, `static/script.js`, `app.py`, `db.py`, `modules/pdf.py` |
| **Claim Register** | **R1, R3** | `templates/index.html`, `static/script.js`, `app.py`, `db.py` |
| **Dashboard** | **R3, R6** | `static/script.js`, `app.py`, `db.py` |
| **Reports** | **R2, R3, R4, R5** | `templates/index.html`, `static/script.js`, `modules/pdf.py`, `worker.py` |
| **Exports** | **R6** | `app.py` (`/export_gstr1_excel`, `/api/admin/backup/download`) |
| **Admin Settings** | **R1, R6** | `templates/index.html`, `static/script.js`, `app.py` |
| **Gmail Sync** | **R3, R5** | `modules/gmail.py`, `worker.py` |

---

## Verification & Acceptance Criteria

- [ ] **AC1 (Insurer Masters):** Employee (`USER`) can open the Insurer Master Modal, add/edit insurers with multiple branch addresses and GST numbers, and select them seamlessly in both Survey Fee Register and Claim Register.
- [ ] **AC2 (Fee Bills):** Fee bills created for any insurer (e.g. IndusInd, Reliance, National) save successfully, immediately appear in the Fee Register list, and download high-quality PDFs.
- [ ] **AC3 (User Isolation):** Employee (`USER`) only sees claims and reports assigned to or created by them in their register. Admin (`SKANOWAR`) has full visibility with a filter for team members.
- [ ] **AC4 (Report Fee Section):** In the Survey Report Generator form, the Fee & Payment Details section is fully functional, editable, and renders correctly on the generated PDF report.
- [ ] **AC5 (Security & RBAC):** Financial dashboard totals and CA tax exports remain 403 Forbidden for employee accounts. All 181+ pytest tests pass.

---
**STOP POINT:** Awaiting user approval on `requirements2026-08-19.md` before proceeding to PHASE 2 (Plan) and PHASE 3 (Implementation).
