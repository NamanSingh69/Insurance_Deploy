import requests
import re
import io

session = requests.Session()
login_page = session.get("https://skinsurance.tech/login")
csrf_token_login = re.search(r'name=["\']csrf_token["\']\s+value=["\']([^"\']+)["\']', login_page.text).group(1)

# Login as USER (Employee)
res_login = session.post("https://skinsurance.tech/login", data={
    "username": "USER",
    "password": "UH65A#DF",
    "csrf_token": csrf_token_login
})
print("1. Login as USER:", res_login.status_code)

home_page = session.get("https://skinsurance.tech/")
token = re.search(r'<meta name="csrf-token" content="([^"]+)"', home_page.text).group(1)
headers = {"X-CSRFToken": token}

# 2. Check Fee Bills (R1)
res_fees = session.get("https://skinsurance.tech/api/fee_bills")
fees = res_fees.json() if res_fees.ok else []
print(f"2. Fee Bills list (R1): Status {res_fees.status_code}, Found {len(fees)} bills")
if fees:
    sample_bill = fees[0]
    print(f"   Sample Bill ID: {sample_bill.get('id')}, Invoice: {sample_bill.get('invoice_no')}, Total: {sample_bill.get('gross_invoice_value')}")

# 3. Test Insurer Master Create & Delete (R2)
res_im_create = session.post("https://skinsurance.tech/api/insurers", json={
    "insurer_name": "United India Insurance Co.",
    "branch_name": "Kalyannagar Branch Test",
    "invoice_prefix": "UIC"
}, headers=headers)
im_id = res_im_create.json().get("id")
print(f"3a. Insurer Master Created (R2): ID {im_id}")
if im_id:
    res_im_del = session.delete(f"https://skinsurance.tech/api/insurers/{im_id}", headers=headers)
    print(f"3b. Insurer Master Deleted by Employee (R2): Status {res_im_del.status_code}, Response: {res_im_del.json()}")

# 4. Test Full Claim Registration (R3)
res_claim_create = session.post("https://skinsurance.tech/api/claims", json={
    "claim_no": "060088312000101NC077",
    "policy_no": "060088312000101",
    "insured_name": "PINAKI SAHA",
    "insured_contact_no": "7980744834",
    "insured_email": "pinaki@example.com",
    "claim_manager_email": "manager@newindia.co.in",
    "claim_manager_phone": "915-52-BD-2799",
    "vehicle_no": "WB-52-BD-2799",
    "vehicle_type": "Private Car",
    "insurer": "The New India Assurance Co. Ltd.",
    "insurer_branch": "Berhampore DO",
    "workshop_name": "GEEKAY AUTO PVT LTD",
    "workshop_phone": "9876543210",
    "date_of_loss": "2026-08-20",
    "survey_type": "final",
    "status": "new_appointment"
}, headers=headers)
print(f"4. Claim Registration (R3): Status {res_claim_create.status_code}, Response: {res_claim_create.json()}")

# 5. Check Dashboard Counters (R3)
res_dash = session.get("https://skinsurance.tech/api/dashboard")
print(f"5. Dashboard (R3): Status {res_dash.status_code}, Counters: {res_dash.json()}")

# 6. Test Intimation PDF Extraction (R4)
from fpdf import FPDF
pdf = FPDF()
pdf.add_page()
pdf.set_font("Helvetica", size=12)
pdf.cell(200, 10, text="Appointment Letter for Motor Survey", new_x="LMARGIN", new_y="NEXT")
pdf.cell(200, 10, text="Claim No: 3126240110", new_x="LMARGIN", new_y="NEXT")
pdf.cell(200, 10, text="Policy No: 060088312000101NC077", new_x="LMARGIN", new_y="NEXT")
pdf.cell(200, 10, text="Insured: TARUN DEBNATH", new_x="LMARGIN", new_y="NEXT")
pdf.cell(200, 10, text="Vehicle: WB-52-BD-2799", new_x="LMARGIN", new_y="NEXT")
pdf.cell(200, 10, text="Insurer: National Insurance Co. Ltd.", new_x="LMARGIN", new_y="NEXT")
pdf.cell(200, 10, text="Workshop: GEEKAY AUTO PVT LTD", new_x="LMARGIN", new_y="NEXT")
pdf_bytes = pdf.output()

files = {'intimation_pdf': ('test_appointment.pdf', io.BytesIO(pdf_bytes), 'application/pdf')}
res_extract = session.post("https://skinsurance.tech/api/claims/extract_intimation", files=files, headers=headers)
print(f"6. Intimation PDF Extraction (R4 & R5): Status {res_extract.status_code}, Response: {res_extract.json()}")