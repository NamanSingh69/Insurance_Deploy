# Motor Survey Management Software — Client User Manual & Release Notes

**Live Platform Domain:** [https://skinsurance.tech](https://skinsurance.tech)  
**Client / Licensed Surveyor:** Sk Anowar Ali (Licence No: `SLA-121784`, Mobile: `8777370714`, Email: `skanowarali93@gmail.com`)  
**Release Version:** `v2.3.0 (August 2026 Production Build)`  
**Last Updated:** August 18, 2026  

---

## 1. Executive Summary & Release Highlights

This production release delivers a complete, professional suite of tools designed specifically for motor survey operations, GST-compliant financial accounting, and field claim administration.

### Summary of New Capabilities & Enhancements:
1. **Official Word Template Fee Bill Generator:** Pixel-perfect replica of the official Microsoft Word survey fee bill template (`rgi fees with signature.docx`), complete with dynamic checkbox line items, automatic conveyance formulas, 18% GST computation, and digital stamp/signature toggles.
2. **Dual Fee Invoicing (Linked & Standalone):** Seamlessly generate bills linked directly to claim survey reports (`Report No.` auto-linked) or standalone survey fee bills with sequential numbering (`NIC-0001`, `OGI-0001`, `UIIC-0001`).
3. **Operational Dashboard & In-Place Drill-Down:** Clicking any KPI metric card instantly filters and displays claim tables directly below without page reloads.
4. **Missing Documents Checklist & 3-Cycle Reminders:** Track pending insured documents (RC, DL, Policy, Claim Form, FIR, Estimate) with automated 7-day reminder notices.
5. **Master Insurer Directory:** Centralized insurance company profiles with saved GSTINs, branch office addresses, and default conveyance reimbursement rates.
6. **Damage Photo Management & PDF Embedding:** Drag-and-drop batch upload for HD vehicle damage photos with optimized background worker rendering in final PDF reports (eliminating "Error loading image" issues).
7. **Role-Based Financial Redaction:** Strict data privacy model where field staff/employee accounts (`USER`) have financial fee registers and revenue KPIs completely redacted, while the Administrator (`NAMAN`) retains full financial control.
8. **Automated 1-Click Deployment Pipeline:** Direct push-to-deploy pipeline running over authenticated HTTPS webhooks with automated asset cache-busting.

---

## 2. Feature Walkthrough & Operating Guide

### 1. Official Motor Survey Fee Bill Generator (Word Template Replica)
* **Where to find:** In the top navigation bar, open the **Survey Fee Register** tab (`#tab-fees`).
* **How it works:**
  - **Dynamic Line-Item Checkboxes:** Check only the fee items you wish to bill. Unchecked items are excluded from calculations and hidden from the generated PDF bill.
    - `1. Final Survey Fees`: Standard professional survey fee.
    - `2. Conveyance Expenses`: Choose between **Flat Rate** or **KM-basis Conveyance** with automatic route calculation text: `<From> to <To> (<KM> x 2 = <TotalKM> km @ Rs. <Rate>/-)`.
    - `3. 2nd visited Conveyance Expenses`: Secondary inspection round-trip conveyance.
    - `4. Re-inspection Fees`: Re-inspection professional charges.
    - `5. Re-inspection Conveyance Expenses`: Re-inspection travel allowance.
    - `6. Photos`: Inspection photography documentation charges.
    - `7. Halting Charges`: Surveyor waiting / detention charges (for long-distance or delayed surveys).
    - `8. Other charges`: Out-of-pocket courier, toll, or postal expenses.
  - **Live GST & Tax Summary:** Dynamic computation of Taxable Subtotal, SAC/HSN Code `997162`, 18% GST, Gross Total, and automatic Indian Rupee currency words conversion.
  - **Digital Stamp & Signature Toggle:** Check `Generate with Signature / Seal` to include your digital surveyor seal and signature sticker on the generated PDF, or uncheck for clean manual signing.
  - **Insurer & Bank Details:** Automatically embeds your Surveyor Code, GSTIN (`19AZZPA2301R1ZM`), and Bank Account details in the official footer.

---

### 2. Dual Invoicing Workflow (Claim-Linked vs Standalone)
* **Linked Fee Bill:** When generating a fee bill from an existing claim or survey report, the `Report No.` (e.g. `K08/G4/24/1365` or `NIC/2026/116`) is automatically linked to the fee bill and displayed on the header.
* **Standalone Fee Bill:** When billing directly from the Survey Fee Register without a claim report, `Report No.` remains optional, and the bill is identified and tracked by its sequential `Bill No.` (e.g., `NIC-0001`).
* **Bidirectional Navigation:** Click any linked Claim Number or Bill Number in the tables to instantly switch between the claim file and its billing record.

---

### 3. Operational Dashboard & In-Place Metric Drill-Down
* **Where to find:** Click the **Dashboard** button on the main navigation.
* **How it works:**
  - The top summary cards show real-time claim volume: *Total Claims*, *Pending Claims*, *Inspection Pending*, *Documents Awaited*, *Report Under Preparation*, *Report Submitted*, and *Closed*.
  - Clicking any KPI card highlights it with an active blue border (`.active-metric-card`) and opens the filtered table **directly below the cards in `#dashboard-drilldown-section`**.
  - Search claims inside the drill-down table by Claim Number, Vehicle Registration, Insured Name, or Insurer.

---

### 4. Missing Documents Checklist & Reminder Notices
* **Where to find:** In the **Claim Register**, click the **Docs** button on any claim row.
* **How it works:**
  - Displays a clean checklist of required documents: *RC Copy*, *Driving Licence*, *Policy Copy*, *Claim Form*, *FIR/Police Report*, *Estimate Copy*, *Satisfaction Voucher*, and custom items.
  - Check or uncheck items to update document collection status in real-time.
  - Tracks 3-cycle reminder notices (1st Notice after 7 days, 2nd Notice after 14 days, Final Notice) with ready-to-copy WhatsApp and Email reminder templates.

---

### 5. Master Insurer Directory & Smart Auto-Prefixing
* **Where to find:** In the **Survey Fee Register**, click **Manage Insurer Masters**.
* **How it works:**
  - Store insurance company profiles: *Insurer Name*, *Branch/Divisional Office Address*, *GSTIN*, *Invoice Prefix*, and *Default Rate/Km*.
  - When creating a fee bill, typing or selecting the Insurer automatically derives the standard acronym prefix (e.g. `National Insurance Company` $\to$ `NIC`) and auto-fills the next sequential invoice number (`NIC-0001`, `NIC-0002`).

---

### 6. Vehicle Damage Photo Management & Robust PDF Embedding
* **Where to find:** In the **Upload & Documents** section under *Vehicle Damage Photos*.
* **How it works:**
  - Drag-and-drop batch upload of HD inspection photos with client-side rate limit throttling to eliminate false storage quota warnings.
  - Background worker PDF generation pipeline normalizes all mobile image formats (HEIC, RGBA, WebP, CMYK JPEG) to ensure high-clarity rendering in final survey reports without "Error loading image" glitches.

---

### 7. Dual-Role Team Permissions & Financial Data Privacy
* **Primary Client Administrator (`SKANOWAR`):** Full unrestricted access to operational claims, all workspace reports, fee billing registers, GSTR-1 & CA Excel exports, user management, and insurer masters.
* **Developer Administrator (`NAMAN`):** Dedicated developer maintenance and technical configuration account.
* **Employee Role (`USER`):** Operational access to search, create, and edit motor survey reports, upload photos, draft fee bills, and generate report/fee PDFs.
  - **Security Restrictions:** Cannot delete reports or fee bills (`403 Forbidden`), cannot access corporate financial KPI dashboards, and cannot download full-business GSTR-1/CA tax accounting files.

---

## 3. Google OAuth & Gmail Sync Setup Guidance

For automatic email claim parsing and Google Drive cloud storage:
- **Authorized Redirect URIs for Web Client:**
  - Google Drive Sync: `https://skinsurance.tech/auth/google/callback`
  - Gmail Sync: `https://skinsurance.tech/auth/gmail/callback`
- In Google Cloud Console, ensure the OAuth Client Type is configured as **Web application** (not Desktop Application) with the two redirect URIs listed above.

---

## 4. User Access Credentials Summary

| Role | Username | Default Password | Permitted Access Scope |
|---|---|---|---|
| **Primary Client Admin** | `SKANOWAR` | `AnowarAdmin@2026` | Full Client Access (All Claims, Fee Register, GSTR-1 Tax Exports, Masters, Settings) |
| **Developer Admin** | `NAMAN` | `69420` | Developer & Maintenance Administration |
| **Employee / Staff** | `USER` | `UH65A#DF` | Operational Access (Search, Create, Edit Reports, Photos, Fee Drafting; No Delete/Tax Exports) |

*(Passwords can be customized anytime in Settings $\to$ User Profile).*

---

## 5. Automated Backups & System Maintenance

1. **Daily Nightly Database Backup:** Automatically dumps and compresses the PostgreSQL database every night to `/root/backups/` with 14-day automatic rotation.
2. **Automated SSL Renewal:** Let's Encrypt SSL certificates renew automatically on Nginx.
3. **Automated 1-Click CI/CD:** Running `python scripts/deploy.py` pushes code to GitHub and executes a secure deployment webhook on the VPS in ~3 seconds.
