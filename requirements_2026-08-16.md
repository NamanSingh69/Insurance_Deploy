# Motor Survey Report Generator — Client Change Requirements (2026-08-16)

**Document Date:** August 16, 2026  
**Source Directory:** `downloads/client changes request/`  
**Speaker Identification:** 
- **Client (Sk Anowar Ali):** Licensed Surveyor & Loss Assessor (demonstrating official Bill template in Microsoft Word, explaining fee line items, and reporting production issues via WhatsApp).
- **Developer / Freelancer:** Recipient of requests and screenshots.

---

## Media Ingestion Inventory

| File Name | Size | Type | Status |
| :--- | :--- | :--- | :--- |
| `Screen Recording 2026-08-16 at 7.24.36 AM.mov` | 179.3 MB | Video (H.264 / AAC, 4m 55s) | Ingested end-to-end natively |
| `Screenshot 2026-08-16 151647.png` | 333.1 KB | PNG Image (WhatsApp Chat 11:30–11:32 AM) | Ingested natively |
| `Screenshot 2026-08-16 151811.png` | 261.5 KB | PNG Image (WhatsApp Chat 08:10–08:14 AM) | Ingested natively |
| `WhatsApp Image 2026-08-16 at 8.10.21 AM.jpeg` | 92.9 KB | JPEG Image (App UI Screenshot) | Ingested natively |
| `WhatsApp Image 2026-08-16 at 11.30.55 AM.jpeg` | 57.5 KB | JPEG Image (PDF Photo Error Screen) | Ingested natively |
| `WhatsApp Image 2026-08-16 at 11.32.30 AM.jpeg` | 153.8 KB | JPEG Image (Google OAuth 400 Error) | Ingested natively |

---

## Numbered Requirements

### R1: Comprehensive Motor Survey Fee Bill Generator & Word Template Matching
- **App Area:** Survey Fee Register (`#tab-fees`) / Reports (`modules/pdf.py`)
- **Source Timestamp:** `Screen Recording 2026-08-16 at 7.24.36 AM.mov` (`00:00` – `04:55`)
- **Client Quote:**
  > *"Ye mera fees template hai... ye jo survey fees hai na ye actually final survey fees hai... Har survey ka, jaise final survey ka bhi local conveyance aur kilometer basis conveyance dono show hoga. Humko jo chahiye hum usme checkbox me right mark karunga... Aise second visit wala bhi same... Re-inspection bhi aur uska conveyance bhi. Photo bhi rahega, halting charges rahega, other charges rahega. Halting charges matlab agar kisi jagah me survey karne gaya, 6 ghanta ruk gaya... to insurance company halting charges deta hai... Ye saare cheez me checkbox rahega. Jo jo cheez fees me show karna chahta hoon usme checkbox me tick mark karunga tabhi wo show hoga aur calculation me lega. HSN/SAC code 997162 aur GST 18%... Signature sticker bhi rahega checkbox me — with signature ya without signature."*
- **Interpretation:** 
  The client requires the Survey Fee Bill generator and PDF output to strictly match their official Word bill format (`rgi fees with signature.docx`):
  1. **Granular Checkbox Toggles & Line Items**:
     - `1. Final Survey Fees` (Amount input)
     - `2. Conveyance Expenses` (Option for **Flat / Local Conveyance** OR **KM-basis Conveyance** with dynamic formula text: `<From> to <To> (<KM> x 2 = <TotalKM> km @ Rs. <Rate>/-)`)
     - `3. 2nd visited Conveyance Expenses` (KM-basis conveyance with route, round-trip km calculation, and rate per km)
     - `4. Re-inspection Fees` (Amount input)
     - `5. Re-inspection Conveyance Expenses` (Local or KM-basis conveyance with calculation text)
     - `6. Photos` (Photo / documentation charges)
     - `7. Halting Charges` (Surveyor waiting / detention charges)
     - `8. Other charges` (e.g. postal charges / courier / toll)
  2. **Calculation & Tax Breakdown**:
     - Live dynamic subtotal of all selected (checked) items = Taxable Amount.
     - Static HSN/SAC Code: `997162`.
     - GST at 18% (`Add: 18% GST`).
     - Gross Total Amount and automated Indian Currency words string (`Rupees: <Amount in words> only`).
  3. **Header, Insurer & Bank Footer Layout**:
     - Professional Surveyor Header with red divider matching the Survey Report format.
     - Addressee block: `To, <Insurer Name>, <Insurer Branch Address>, GSTIN: <Insurer GSTIN>`.
     - 2-Column Claim metadata box: Policy No, Insured Name, Claim No, Vehicle No, Date of Accident.
     - Footer: Surveyor Code No, Surveyor GSTIN (`19AZZPA2301R1ZM`), and Bank Account details (Account Number, Bank Name, Branch, IFSC code).
  4. **Digital Signature & Stamp Toggle**:
     - Checkbox option (`Generate with Signature / Seal`) allowing the user to produce signed bills with digital seal or clean unsigned bills for manual signing.
- **Ambiguities:**
  - Default rate per km is typically Rs. 10/km (or fetched from Insurer Master).
  - Both standalone fee bills and claim-linked fee bills should support this exact PDF output format.
- **Risk Rating:** Medium (Core financial PDF layout and UI form expansion).

---

### R2: Report Number Linking vs Standalone Bill Number Workflow
- **App Area:** Survey Fee Register (`#tab-fees`) / Claim Register (`#tab-claims`) / Reports
- **Source Timestamp:** `Screen Recording 2026-08-16 at 7.24.36 AM.mov` (`02:54` – `04:45`)
- **Client Quote:**
  > *"Abhi question aa raha hai ki report number kahan se aayega... Agar only fees karenge to uska kaise hoga... Report ke saath jo fees ho raha hai wo is fees section ke saath patch hona hai. Report number is position me aa jayega... Aur agar only fees banayega to report number ka zaroorat nahi hai, only bill number aayega. Kyunki fees se main us report ko track kar paun isliye fees me report number rehta hai."*
- **Interpretation:**
  1. **Dual Invoice Workflow**:
     - **Linked Workflow (Report + Fee Bill)**: When generating a fee bill from an existing claim or survey report, the `Report No` (e.g. `K08/G4/24/1365` or `NIC/2026/116`) is automatically linked, displayed on the bill header, and saved in the fee record. The `Bill No` (e.g. `KG-2365` or `NIC-0001`) increments sequentially based on the insurer prefix.
     - **Standalone Workflow (Direct Fee Bill)**: When generating a fee bill directly from the Survey Fee Register without an existing claim report, `Report No` is optional (displays blank or N/A), and the bill is identified and tracked by its sequential `Bill No`.
  2. **Bidirectional Navigation**: In the Claim Register and Fee Register tables, users should be able to see the linked Report No / Bill No and click to view/open the corresponding fee bill or claim.
- **Ambiguities:** None.
- **Risk Rating:** Low (Workflow and metadata association).

---

### R3: Fix Damage Photo Rendering in Generated PDF Reports ("Error loading image")
- **App Area:** Reports / Photo Attachments (`modules/pdf.py`, `modules/assets.py`, `app.py`, `worker.py`)
- **Source:** `Screenshot 2026-08-16 151647.png`, `WhatsApp Image 2026-08-16 at 11.30.55 AM.jpeg` (11:30–11:31 AM)
- **Client Quote:**
  > *"Problem in image"*  
  > *"In online version"*
- **Observed Behavior:** On the live production site `https://skinsurance.tech`, generating a final survey report PDF containing damage photos renders 4 empty bordered boxes on the "First inspection photo (WB-30-Q-9890)" page with the text `"Error loading image"`.
- **Root Cause Analysis:**
  1. In `modules/pdf.py` (`add_inspection_photos`), image loading from private asset storage (`/assets/<id>/...`) passes `user_data_snapshot` to `get_accessible_asset_content(asset_id, user_id, ws_admin_id)`. When jobs run asynchronously in `worker.py` or when employee accounts generate PDFs, `ws_admin_id` or session credentials may be mismatched or missing from the background job payload.
  2. Uploaded image formats from mobile devices (HEIC, WebP, CMYK JPEG, RGBA PNG) or missing stream resets (`seek(0)`) cause PIL / FPDF `pdf_obj.image()` to throw an exception, silently falling back to the `"Error loading image"` box.
- **Resolution Plan:**
  1. Update `modules/pdf.py` to robustly resolve asset IDs across workspace scoping and verify stream integrity with automatic PIL RGB normalization (`Image.convert('RGB')`).
  2. Ensure worker payload passes explicit `workspace_admin_id` and `user_id` so background PDF generation has full asset read access.
  3. Support all photo URL representations (`/assets/`, `/api/assets/`, `/proxy_image/`, `/local_image/`, base64).
- **Ambiguities:** None (Deterministic bug).
- **Risk Rating:** Medium (Core PDF rendering pipeline).

---

### R4: Fix Google OAuth 400 `redirect_uri_mismatch` on Production Domain
- **App Area:** Admin Settings (`#tab-settings`) / Gmail Sync / Google Drive OAuth (`app.py`)
- **Source:** `Screenshot 2026-08-16 151647.png`, `WhatsApp Image 2026-08-16 at 11.32.30 AM.jpeg` (11:32 AM)
- **Observed Error:**
  > *"Sign in with Google - Access blocked: This app's request is invalid"*  
  > *"Error 400: redirect_uri_mismatch"* (User: `pranayiitkgp@gmail.com`)
- **Root Cause Analysis:**
  1. The Google Cloud OAuth 2.0 Client credentials downloaded by the client were configured as an "Installed / Desktop Application" (`redirect_uris: ["http://localhost"]`) instead of a "Web application" with `https://skinsurance.tech/auth/google/callback` and `https://skinsurance.tech/auth/gmail/callback`.
  2. Flask's `request.host` behind Nginx reverse proxy may construct redirect URIs with mismatched ports or schemes if `X-Forwarded-Proto` is not properly handled by `ProxyFix`.
- **Resolution Plan:**
  1. Enforce canonical production redirect URIs in `app.py`:
     - Google Drive: `https://skinsurance.tech/auth/google/callback`
     - Gmail Sync: `https://skinsurance.tech/auth/gmail/callback`
  2. Ensure `werkzeug.middleware.proxy_fix.ProxyFix` is active in `app.py` so reverse proxy headers (`X-Forwarded-Proto: https`, `X-Forwarded-Host: skinsurance.tech`) are respected.
  3. Provide exact Google Cloud Console setup guidance for the client to register the authorized redirect URIs in their Web Application Client ID.
- **Ambiguities:** None.
- **Risk Rating:** Low (Configuration & proxy fix).

---

### R5: Role-Based Financial Segregation Guidance & Employee UI Clarification
- **App Area:** Dashboard (`#tab-dashboard`) / Survey Fee Register (`#tab-fees`) / User Management
- **Source:** `Screenshot 2026-08-16 151811.png`, `WhatsApp Image 2026-08-16 at 8.10.21 AM.jpeg` (08:10 AM)
- **Client Quote:**
  > *"fees section show nahi karraha hai"*
- **Observed Behavior:** The client logged in as `USER` (the default employee account) on Mac Safari/Chrome and noticed that the "Survey Fee Register" workspace card and navigation tab were not visible.
- **Root Cause & Architectural Rule:**
  - As established in the system architecture and binding architectural constraints:
    > *"Financial data redacted from employee API responses; employee saves must never overwrite financial records."*
  - The Surveyor Administrator account (`NAMAN`) has full access to the Survey Fee Register, Insurer Masters, and financial metrics. The Employee account (`USER`) is intentionally restricted to operational claim management and report editing to prevent employee leakage of business fee schedules.
- **Resolution Plan:**
  1. Maintain strict backend financial redaction and role-based access control (Admin only for Survey Fee Register).
  2. Add clear admin guidance in the User Manual and release notes reminding the client to log in with their Admin account (`NAMAN`) to access fee billing and insurer master tools.
  3. Add an informative subtle workspace indicator in the user profile menu showing the active role (`Role: Administrator` vs `Role: Employee`) with quick instructions.
- **Ambiguities:** None.
- **Risk Rating:** Low (Instructional / UI clarity).

---

## Requirement Mapping Table

| ID | Title | App Area | Files / Routes Affected | Financial Redaction Impact | Risk Rating |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **R1** | Word Template Matching Fee Bill Generator | Survey Fee Register / PDF | `templates/index.html`, `static/script.js`, `modules/pdf.py`, `app.py` | **Admin Only** (Fee Register is strictly admin-scoped) | Medium |
| **R2** | Report No Linking & Standalone Bill Numbers | Survey Fee Register / Claim Register | `templates/index.html`, `static/script.js`, `db.py`, `app.py` | **Admin Only** | Low |
| **R3** | Fix Damage Photo Rendering in PDF Reports | Reports / Assets / PDF Generator | `modules/pdf.py`, `modules/assets.py`, `worker.py`, `app.py` | None (Claim photos accessible to both roles) | Medium |
| **R4** | Fix Google OAuth 400 redirect_uri_mismatch | Admin Settings / Gmail & Drive | `app.py`, `vps_setup/nginx.conf`, Google Cloud Console | Admin Only | Low |
| **R5** | Role-Based Financial Segregation Guidance | Dashboard / User Profile / Manual | `templates/index.html`, `docs/CLIENT_USER_MANUAL_AND_CHANGELOG.md` | Preserves 100% financial redaction for employees | Low |

---

## Next Steps (Awaiting Approval)
Upon your approval of this requirements specification, we will proceed to **Phase 2 (Detailed Implementation Plan)** mapping out exact database migrations, routes, FPDF2 layout coordinates, and test cases.
