# Motor Survey Report Generator — Client Change Requirements (2026-08-14)

**Document Date:** August 14, 2026  
**Source Media:** `downloads/client changes request/WhatsApp Video 2026-08-14 at 8.45.27 AM.mp4` (265 seconds screen recording + audio commentary)  
**Speaker Identification:** Client (demonstrating system behaviors on `https://skinsurance.tech` and narrating requested improvements in Hindi)  

---

## Media Ingestion Inventory

| File Name | Size | Type | Status |
| :--- | :--- | :--- | :--- |
| `WhatsApp Video 2026-08-14 at 8.45.27 AM.mp4` | 22.0 MB | MP4 Video (H.264 / AAC, 4m 25s) | Ingested end-to-end natively |

---

## Numbered Requirements

### R1: In-Place Interactive Claim Drill-Down on Dashboard
- **App Area:** Dashboard (`#tab-dashboard`) / Claim Register (`#tab-claims`)
- **Source Timestamp:** `00:10` – `01:16`
- **Client Quote:** 
  > *"jab usko click kiya dashboard mein wo claim ke upar... ye dekhiye wo hat ja raha hai. Humko fir dusra mein lena hai to humko fir yahan par aakar idhar aana hai, fir idhar par pending mein touch karna hai, fir wo hat ja raha hai... fir idhar niche aana padega... main chah raha hoon ye jo dashboard ye jo cheez dikha raha hai, ye dikhai dega aur ye niche aisa jo list hai niche nikal jaayega... to jisme jo touch karenge easily hum usko dekh sakte hain, nahi to humko fir udhar jaana pad raha hai."*
- **Interpretation:** Currently, clicking any operational KPI card on the Dashboard triggers a tab switch to `#tab-claims`. This forces the user to navigate back and forth between workspaces to check different status metrics. The client requests that the Dashboard KPI cards remain visible at the top, and clicking any KPI card (Total claims, Pending claims, New appointment, Inspection pending, Documents awaited, Report under preparation, Submitted, Closed) should dynamically filter and display the interactive claims list directly below the KPI cards on the Dashboard page itself, with the active metric highlighted.
- **Ambiguities:** The dedicated Claim Register tab should remain intact for full-page claim search and advanced filtering.
- **Risk Rating:** Low (Frontend UI/UX enhancement).

---

### R2: Fix JavaScript ReferenceError in Pending Documents Checklist Modal
- **App Area:** Claim Register (`#tab-claims`) / Dashboard
- **Source Timestamp:** `00:30` – `00:40`
- **Observed Behavior:** Clicking the `Docs` action on a claim in the table threw a red toast error: *"Failed to load pending documents checklist."*
- **Root Cause:** In `static/script.js` line 2771–2778, the variable is defined as `const reminderInfo = data.reminder_info || {};` but subsequent lines reference `reminder_info.reminder_count`, triggering an uncaught `ReferenceError: reminder_info is not defined`.
- **Interpretation:** Correct variable names to `reminderInfo` in `openPendingDocsModal` so the documents modal opens cleanly and displays pending checklist items and reminder counts.
- **Ambiguities:** None (Deterministic bug).
- **Risk Rating:** Low (Bug fix).

---

### R3: Insurer Master Management Accessibility & Help Guidance
- **App Area:** Survey Fee Register (`#tab-fees`) / Admin Settings
- **Source Timestamp:** `01:54` – `02:25`, `03:55` – `04:03`
- **Client Quote:**
  > *"Master put karke kaise karun? Input kaise karun? Yahan par... yahan to insurance company aayega, lekin idhar jo details deke rakhunga wo kahan par karna hai? Ye thoda bata dijiyega."*
- **Interpretation:** The client was confused about where Insurer Master records (Insurer name, branch name, GSTIN, invoice prefix, default conveyance rate) are created and stored. Enhance the Survey Fee Register UI with prominent visual guidance and a direct "+ Manage Insurer Masters" action button, with clear inline hints explaining that selecting an Insurer Master automatically populates branch, GSTIN, and sequential invoice numbers.
- **Ambiguities:** None.
- **Risk Rating:** Low (UX/UI clarity).

---

### R4: Auto-Prefix Generation and Insurer Matching on Manual Typing in Survey Fee Register
- **App Area:** Survey Fee Register (`#tab-fees`)
- **Source Timestamp:** `02:26` – `03:54`
- **Client Quote:**
  > *"National Insurance Company yahan par default lega... NIC... uske baad number lega... jaise NIC-0001. Aise maan lijiye wo bhi le lega, default le lega. Maan lijiye isko Oriental General Insurance... to ye le lega OGI-0001... matlab first digit wala lega default mein."*
- **Interpretation:** 
  1. When selecting an Insurer Master OR typing an Insurer Name that matches a master record, auto-fill the Insurer GSTIN, Branch Address, and fetch the next sequential invoice number using the insurer's prefix (e.g. `NIC-0001`, `OGI-0001`).
  2. When typing a new or non-master insurer name (e.g. "National Insurance Company", "Oriental General Insurance Company", "United India Insurance", "Liberty General Insurance"), auto-derive a smart prefix from the initials of significant words (e.g. `NIC`, `OGIC` / `OGI`, `UIIC` / `UII`, `LGIC`) and generate the next invoice number default formatted as `<PREFIX>-0001`.
- **Ambiguities:** Prefixes should be editable by the user if a custom format is needed.
- **Risk Rating:** Medium (Requires client-side prefix generator + backend prefix sequence API check).

---

### R5: Professional Fee Stepper Usability & Live Fee Breakdown Summary
- **App Area:** Survey Fee Register (`#tab-fees`)
- **Source Timestamp:** `04:04` – `04:18`
- **Client Quote:**
  > *"Ye kya hai samajh nahi aa raha hai... 0.01... matlab ye total dikhayega ya humko theek samajh nahi aa raha... thoda dekhiye."*
- **Interpretation:**
  1. In `templates/index.html`, the Professional Fee input had `step="0.01"` without default value, causing the browser number spinner to increment by 1 paisa (`0.01`), confusing the user. Update step to `step="1"` (or `step="any"` allowing rupee amounts e.g., 500, 1000, 1500) and provide clean placeholder text.
  2. Add a clear real-time live calculation breakdown card inside the Survey Fee form showing:
     `Professional Fee + Conveyance + Photocopy = Taxable Amount + GST (18%) = Gross Total`, updating dynamically on every keystroke.
- **Ambiguities:** None.
- **Risk Rating:** Low.

---

### R6: Diagnosis & Fix for False Google Drive Quota Alert & Photo Upload Throttling
- **App Area:** Reports / Photo Attachments (`#upload_photo`, `static/script.js`)
- **Source:** User screenshots (`1.jpeg, 2.jpeg... Failed to upload... Google Drive storage quota being full`)
- **Root Cause Diagnosis:**
  1. The `/upload_photo` route was strictly throttled by `@limiter.limit("30 per hour")`. Multi-photo vehicle damage reports (typically 10–30 photos) exhausted this quota after a few uploads, causing subsequent image uploads to fail with HTTP 429.
  2. The frontend error handler in `handlePhotoSelection` had a legacy hardcoded fallback alert claiming failures were due to "Google Drive storage quota being full", even though image storage was migrated to private asset storage (`modules/assets.py`).
- **Resolution:**
  1. Increased the `/upload_photo` rate limit in `app.py` to `@limiter.limit("300 per hour; 60 per minute")` for authorized survey users.
  2. Updated frontend error handling to report actual server diagnostic errors (e.g. file format/size/network) rather than misleading Google Drive quota alerts.
- **Ambiguities:** None.
- **Risk Rating:** Low.

---

## Requirement Mapping Table

| ID | Title | App Area | Files / Routes Affected | Financial Redaction Impact | Risk Rating |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **R1** | In-Place Dashboard Claim Drill-Down | Dashboard / Claim Register | `templates/index.html`, `static/script.js` | None (Claims list respects employee vs admin scoping) | Low |
| **R2** | Fix Pending Docs Checklist ReferenceError | Claim Register / Dashboard | `static/script.js` | None | Low |
| **R3** | Insurer Master Management Usability | Survey Fee Register | `templates/index.html`, `static/script.js` | None | Low |
| **R4** | Smart Auto-Prefix & Typing Match for Invoice No | Survey Fee Register | `static/script.js`, `app.py` (`/api/insurers/next-invoice-no`) | Admin only (Fee register remains restricted to Admin) | Medium |
| **R5** | Professional Fee Input & Live Calculation Box | Survey Fee Register | `templates/index.html`, `static/script.js` | Admin only | Low |
| **R6** | Photo Upload Rate Limit & Accurate Diagnostics | Reports / Photos | `app.py`, `static/script.js` | None | Low |


