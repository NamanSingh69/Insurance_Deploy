# Motor Survey Management Software — Client User Manual & Release Notes

**Live Platform Domain:** [https://skinsurance.tech](https://skinsurance.tech)  
**Client / Surveyor:** Sk Anowar Ali (Licence No: `SLA-121784`, Mobile: `8777370714`, Email: `skanowarali93@gmail.com`)  
**Release Version:** `v2.2.0 (August 2026 Production Build)`

---

## 1. Executive Summary & New Enhancements Overview

This updated release introduces key workflow optimizations, granular financial tools, instant document checklist tracking, and zero-friction cloud deployment.

### Summary of New Features & Enhancements (R1 – R6)
1. **R1 (Dashboard In-Place Metric Drill-Down):** Clicking any dashboard KPI card filters claims instantly below the metric cards without losing your place.
2. **R2 (Missing Documents Checklist Modal):** Granular, per-claim document checklist with dynamic custom item additions and automated reminder tracking.
3. **R3 (Insurer Master Guidance & Setup):** A centralized Master Insurer directory to store GSTINs, branch addresses, and default conveyance rates.
4. **R4 (Smart Auto-Prefix & Sequential Invoice Numbering):** Automatic acronym derivation (`NIC-0001`, `OGI-0001`, `UIIC-0001`) with sequential number generation.
5. **R5 (Professional Fee Stepper & Live Calculation Summary):** Whole-rupee increments (`step="1"`) with dynamic live recalculation card showing Taxable Amount, GST (18%), and Gross Total.
6. **R6 (Damage Photo Upload Diagnostics & Throttling):** Drag-and-drop HD vehicle photo uploader with client-side throttling to prevent false storage quota alerts.
7. **Role Security & Financial Redaction:** Strict role-based access where employee accounts (`USER`) have financial fee registers and KPI metrics completely redacted.
8. **Automated Zero-Friction CI/CD Pipeline:** Real-time push-to-deploy pipeline running over HTTPS webhook with automated asset cache-busting.

---

## 2. Feature Walkthrough & Visual Proof

### 1. Operational Dashboard & In-Place Drilldown (Requirement R1)
* **Where to find:** Click the **Dashboard** button on the main navigation.
* **How it works:**
  - The top summary cards show live metrics: *Total Claims*, *Pending Claims*, *Inspection Pending*, *Documents Awaited*, *Report Under Preparation*, *Report Submitted*, and *Closed*.
  - When you click on any card (e.g. *Documents Awaited*), the card is highlighted with a blue border (`.active-metric-card`), and the filtered table opens **directly below the cards in `#dashboard-drilldown-section`**.
  - You can search inside the filtered table or click any claim to view details immediately.

![Dashboard In-Place Drilldown](file:///c:/Users/namsi/Desktop/Freelance/Insurance%20-%20SK/docs/evidence_r1_dashboard_drilldown.png)

---

### 2. Missing Documents Checklist & Reminders Modal (Requirement R2)
* **Where to find:** In the **Claim Register**, click the **Docs** button on any claim row.
* **How it works:**
  - Displays a clean checklist of required documents: *RC Copy*, *Driving Licence*, *Policy Copy*, *Claim Form*, *FIR/Police Report*, *Estimate Copy*, *Satisfaction Voucher*, and custom items.
  - Check/uncheck items to update document collection status in real-time.
  - Track reminder notices (1st Notice, 2nd Notice, Final Notice) sent to the insured and claim manager.

![Pending Documents Modal](file:///c:/Users/namsi/Desktop/Freelance/Insurance%20-%20SK/docs/evidence_r2_docs_modal.png)

---

### 3. Master Insurer Directory & Guidance (Requirement R3)
* **Where to find:** In the **Survey Fee Register**, click **Manage Insurer Masters** (`.open-insurer-master-modal-btn`).
* **How it works:**
  - Configure insurance company profiles: *Insurer Name*, *Branch/Divisional Office Address*, *GSTIN*, *Invoice Prefix*, and *Default Rate/Km*.
  - Once saved, selecting an insurer automatically pre-fills all billing and address fields in the fee form.

![Insurer Master Management Modal](file:///c:/Users/namsi/Desktop/Freelance/Insurance%20-%20SK/docs/evidence_r3_insurer_master_btn.png)

---

### 4. Smart Auto-Prefix & Sequential Invoice Numbering (Requirement R4)
* **Where to find:** In the **Survey Fee Register** form under the *Insurer* input field.
* **How it works:**
  - Typing an insurer name (e.g., *National Insurance Company*) auto-derives the standard acronym prefix (`NIC`) or matches your saved master prefix.
  - The system queries the database and auto-fills the next available sequential number (e.g., `NIC-0001`, `NIC-0002`).

![Smart Invoice Auto-Prefix](file:///c:/Users/namsi/Desktop/Freelance/Insurance%20-%20SK/docs/evidence_r4_auto_invoice_prefix.png)

---

### 5. Professional Fee Stepper & Live Calculation Summary (Requirement R5)
* **Where to find:** In the **Survey Fee Register** form under fee breakdown inputs.
* **How it works:**
  - **Whole Rupee Enforced:** The *Professional Fee*, *Conveyance*, and *Photocopy* fields use whole integer steps (`step="1"`), preventing accidental fractions.
  - **Conveyance Combined Mode:** Enter flat rate conveyance or use the **Km Formula** ($\text{One-way Km} \times 2 \times \text{Visits} \times \text{Rate/Km}$).
  - **Live Breakdown Card:** As you type, the summary card immediately calculates:
    $$\text{Taxable Amount} = \text{Professional Fee} + \text{Conveyance} + \text{Photocopy}$$
    $$\text{GST (18\%)} = \text{Taxable Amount} \times 0.18$$
    $$\text{Gross Total} = \text{Taxable Amount} + \text{GST (18\%)}$$

![Live Fee Calculation Breakdown](file:///c:/Users/namsi/Desktop/Freelance/Insurance%20-%20SK/docs/evidence_r5_live_fee_calculation.png)

---

### 6. Damage Photo Upload Diagnostics & Throttling (Requirement R6)
* **Where to find:** In the **Upload & Documents** section under *Vehicle Damage Photos*.
* **How it works:**
  - Allows smooth batch drag-and-drop of HD inspection photos.
  - Client-side adaptive throttling ensures uploads complete reliably without hitting rate limits or triggering false storage quota errors.

![Damage Photo Upload](file:///c:/Users/namsi/Desktop/Freelance/Insurance%20-%20SK/docs/evidence_r6_photo_upload.png)

---

### 7. Dual-Role Team Permissions & Financial Redaction
* **Administrator Role (`NAMAN`):** Full control over claims, fee registers, GST exports, user accounts, and billing masters.
* **Employee Role (`USER`):** Operational access to create and edit motor survey reports and update claim statuses.
  - **Financial Guard:** The Survey Fee Register tab and financial revenue KPIs are completely hidden. Direct API requests to billing routes return `403 Forbidden`.

![Employee Financial Redaction](file:///c:/Users/namsi/Desktop/Freelance/Insurance%20-%20SK/docs/evidence_employee_financial_redaction.png)

---

## 3. Automated Backups & System Maintenance

1. **Daily Nightly Database Backup:**
   - Automatically dumps and compresses the PostgreSQL database every night to `/root/backups/`.
   - Rotates and purges backup archives older than 14 days to conserve disk space.
2. **Automated SSL Renewal:**
   - Let's Encrypt SSL certificates renew automatically via `certbot.timer`.
3. **Automated CI/CD:**
   - Every code update pushed to GitHub deploys live in ~3 seconds via the verified webhook.

![GitHub Webhook Active](file:///c:/Users/namsi/Desktop/Freelance/Insurance%20-%20SK/docs/webhook_delivery_1_1786828833808.png)

---

## 4. User Credentials Summary

| Role | Username | Password | Permissions |
|---|---|---|---|
| **Admin** | `NAMAN` | `69420` | Full Access (Operations, Fee Register, GSTR-1, Settings) |
| **Employee** | `USER` | `UH65A#DF` | Operational Access (Claim Register, Survey Reports, PDF Download) |

*(Passwords can be customized anytime in Settings $\to$ User Profile).*
