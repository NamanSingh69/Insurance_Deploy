import requests
import re
import json

session = requests.Session()
login_page = session.get("https://skinsurance.tech/login")
csrf_token_login = re.search(r'name=["\']csrf_token["\']\s+value=["\']([^"\']+)["\']', login_page.text).group(1)

# Login as USER
res = session.post("https://skinsurance.tech/login", data={
    "username": "USER",
    "password": "UH65A#DF",
    "csrf_token": csrf_token_login
})

# Get authenticated page to get session CSRF token
home_page = session.get("https://skinsurance.tech/")
csrf_token_app = re.search(r'<meta name="csrf-token" content="([^"]+)"', home_page.text)
token = csrf_token_app.group(1) if csrf_token_app else csrf_token_login
print("Authenticated CSRF token extracted:", token is not None)

headers = {"X-CSRFToken": token}

print("\n=== 1. Testing Insurer Master Creation & Deletion as Employee (USER) ===")
create_ins = session.post("https://skinsurance.tech/api/insurers", json={
    "insurer_name": "Test Insurance Co",
    "branch_name": "Test Branch",
    "invoice_prefix": "TST"
}, headers=headers)
print("Create Insurer Master:", create_ins.status_code, create_ins.json())
ins_id = create_ins.json().get("id")

if ins_id:
    del_ins = session.delete(f"https://skinsurance.tech/api/insurers/{ins_id}", headers=headers)
    print("Delete Insurer Master as USER (R2 Fix):", del_ins.status_code, del_ins.json())

print("\n=== 2. Testing Claim Creation as Employee (USER) ===")
create_claim = session.post("https://skinsurance.tech/api/claims", json={
    "claim_no": "TEST-CLAIM-2026-AUG21",
    "policy_no": "POL-999000",
    "insured_name": "TEST INSURED",
    "vehicle_no": "WB-99-TEST",
    "insurer": "Test Insurance Co",
    "survey_type": "final",
    "status": "new_appointment"
}, headers=headers)
print("Create Claim:", create_claim.status_code, create_claim.json())
rep_id = create_claim.json().get("report_id")

if rep_id:
    # Verify in claim list
    clm_list = session.get("https://skinsurance.tech/api/claims")
    print("Claims list total:", clm_list.json().get("total"))
    
    # Clean up test claim
    del_claim = session.delete(f"https://skinsurance.tech/api/reports/{rep_id}", headers=headers)
    print("Cleanup test report:", del_claim.status_code)