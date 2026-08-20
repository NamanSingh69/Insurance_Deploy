import requests
import json
import re

BASE_URL = "https://skinsurance.tech"

def get_session_and_login(username, password):
    s = requests.Session()
    r_get = s.get(f"{BASE_URL}/login")
    csrf_match = re.search(r'name=["\']csrf_token["\']\s+value=["\']([^"\']+)["\']', r_get.text) or \
                 re.search(r'value=["\']([^"\']+)["\']\s+name=["\']csrf_token["\']', r_get.text) or \
                 re.search(r'window\.__CSRF_TOKEN__\s*=\s*["\']([^"\']+)["\']', r_get.text)
    csrf_token = csrf_match.group(1) if csrf_match else ''
    
    headers = {'X-CSRFToken': csrf_token} if csrf_token else {}
    data = {"username": username, "password": password}
    if csrf_token:
        data["csrf_token"] = csrf_token
    
    r_post = s.post(f"{BASE_URL}/login", data=data, headers=headers)
    assert r_post.status_code in (200, 302)
    
    # Get index page to extract page CSRF token
    r_idx = s.get(f"{BASE_URL}/")
    idx_csrf_match = re.search(r'window\.__CSRF_TOKEN__\s*=\s*["\']([^"\']+)["\']', r_idx.text) or \
                     re.search(r'name=["\']csrf_token["\']\s+value=["\']([^"\']+)["\']', r_idx.text)
    if idx_csrf_match:
        page_csrf = idx_csrf_match.group(1)
        s.headers.update({'X-CSRFToken': page_csrf})
    elif csrf_token:
        s.headers.update({'X-CSRFToken': csrf_token})
        
    return s

print("1. Testing Healthz...")
r = requests.get(f"{BASE_URL}/healthz")
print(f"Healthz: {r.status_code} -> {r.json()}")
assert r.status_code == 200

print("\n2. Logging in as Admin (SKANOWAR)...")
s_admin = get_session_and_login("SKANOWAR", "AnowarAdmin@2026")
print(f"Admin Session Authenticated with CSRF Token: {s_admin.headers.get('X-CSRFToken', '')[:10]}...")

print("\n3. Fetching Insurer Masters...")
r_ins = s_admin.get(f"{BASE_URL}/api/insurers")
assert r_ins.status_code == 200
insurers_list = r_ins.json().get('insurers', [])
print(f"Insurers ({r_ins.status_code}): {len(insurers_list)} configured")

print("\n4. Saving/Updating Insurer Master with Surveyor Code (R1)...")
test_im = {
    "insurer_name": "National Insurance Co. Ltd.",
    "branch_name": "Kolkata Hub",
    "invoice_prefix": "NIC",
    "gstin": "19AAACN2027K1ZV",
    "state_code": "19",
    "surveyor_code": "2075995",
    "default_conveyance_rate": 10.0,
    "branch_address": "Ruby More, Kolkata"
}
r_save_im = s_admin.post(f"{BASE_URL}/api/insurers", json=test_im)
print(f"Save Insurer Master ({r_save_im.status_code}): {r_save_im.text}")
assert r_save_im.status_code in (200, 201)
saved_im = r_save_im.json()
print(f"Saved Insurer ID: {saved_im.get('id')}")

# Verify surveyor_code is returned in get_insurer_masters
r_ins2 = s_admin.get(f"{BASE_URL}/api/insurers")
insurers2 = r_ins2.json().get('insurers', [])
nic_master = next((im for im in insurers2 if im.get('invoice_prefix') == 'NIC'), None)
assert nic_master is not None
print(f"Verified Surveyor Code in DB: {nic_master.get('surveyor_code')}")
assert nic_master.get('surveyor_code') == "2075995"

print("\n5. Testing PDF preview generation with surveyor code (R2)...")
pdf_payload = {
    "invoice_no": "NIC/2026/0001",
    "invoice_date": "2026-08-20",
    "report_no": "NIC/REP/2026/001",
    "insurer_name": "National Insurance Co. Ltd.",
    "insurer_gst": "19AAACN2027K1ZV",
    "insured_name": "Subrata Ghosh",
    "policy_no": "POL-998877",
    "claim_no": "CLM-998877",
    "vehicle_no": "WB-02-AK-9999",
    "surveyor_code": "2075995",
    "fee_items": [{"name": "1. Final Survey Fees :", "amount": 2000.0}],
    "taxable_amount": 2000.0,
    "gst_pc": 18.0,
    "gst_amount": 360.0,
    "total_amount": 2360.0,
    "preview": True
}
r_pdf = s_admin.post(f"{BASE_URL}/generate_fee_pdf?preview=true", json=pdf_payload)
print(f"PDF Preview ({r_pdf.status_code}): Content-Type={r_pdf.headers.get('Content-Type')}, Content-Disposition={r_pdf.headers.get('Content-Disposition')}, Size={len(r_pdf.content)} bytes")
assert r_pdf.status_code == 200
assert r_pdf.headers.get('Content-Type') == 'application/pdf'
assert 'inline' in r_pdf.headers.get('Content-Disposition', '')

print("\n6. Saving Fee Bill to Database...")
r_save_bill = s_admin.post(f"{BASE_URL}/api/fee_bills", json=pdf_payload)
print(f"Save Fee Bill ({r_save_bill.status_code}): {r_save_bill.text}")
assert r_save_bill.status_code in (200, 201)
bill_res = r_save_bill.json()
bill_id = bill_res.get('id')
print(f"Saved Fee Bill ID: {bill_id}")

print("\n7. Testing Fee Bill Payment Lifecycle & Remarks update (R3)...")
pay_payload = {
    "payment_status": "partially_paid",
    "payment_date": "2026-08-20",
    "amount_received": 1800.0,
    "tds_amount": 200.0,
    "payment_reference": "UTR99887766",
    "payment_remarks": "Conveyance deduction of Rs 360 disallowed by DO manager."
}
r_pay = s_admin.post(f"{BASE_URL}/api/fee_bills/{bill_id}/payment", json=pay_payload)
print(f"Payment Update ({r_pay.status_code}): {r_pay.text}")
assert r_pay.status_code == 200

# Verify payment details in get fee bills
r_fees = s_admin.get(f"{BASE_URL}/api/fee_bills")
fees_data = r_fees.json()
updated_bill = next((b for b in fees_data if b.get('id') == bill_id), None)
assert updated_bill is not None
print(f"Verified Payment Status in DB: {updated_bill.get('payment_status')}")
print(f"Verified Amount Received: {updated_bill.get('amount_received')}")
print(f"Verified TDS Amount: {updated_bill.get('tds_amount')}")
print(f"Verified Outstanding Amount: {updated_bill.get('outstanding_amount')}")
print(f"Verified Payment Remarks: {updated_bill.get('payment_remarks')}")
assert updated_bill.get('payment_status') == 'partially_paid'
assert updated_bill.get('payment_remarks') == "Conveyance deduction of Rs 360 disallowed by DO manager."

print("\n8. Testing Employee Login & Multi-tenant RBAC (USER)...")
s_emp = get_session_and_login("USER", "UH65A#DF")
r_emp_ins = s_emp.get(f"{BASE_URL}/api/insurers")
print(f"Employee Insurers access ({r_emp_ins.status_code}): {len(r_emp_ins.json().get('insurers', []))} insurers visible")
assert r_emp_ins.status_code == 200

# Verify employee cannot see financial summaries on dashboard (keys are completely redacted)
r_emp_dash = s_emp.get(f"{BASE_URL}/api/dashboard")
print(f"Employee Dashboard Status ({r_emp_dash.status_code})")
assert r_emp_dash.status_code == 200
dash = r_emp_dash.json()
print(f"Employee Dashboard Total Invoiced (should be None/redacted): {dash.get('total_invoiced')}")
assert 'total_invoiced' not in dash
assert 'amount_received' not in dash
assert 'outstanding_fees' not in dash

print("\n============================================================")
print(">>> ALL PRODUCTION VERIFICATION CHECKS PASSED FLAWLESSLY! <<<")
print("============================================================")
