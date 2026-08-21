import requests
import re

session = requests.Session()
login_page = session.get("https://skinsurance.tech/login")
csrf_token = re.search(r'name=["\']csrf_token["\']\s+value=["\']([^"\']+)["\']', login_page.text).group(1)

session.post("https://skinsurance.tech/login", data={
    "username": "USER",
    "password": "UH65A#DF",
    "csrf_token": csrf_token
})

home_page = session.get("https://skinsurance.tech/")
token = re.search(r'<meta name="csrf-token" content="([^"]+)"', home_page.text).group(1)
headers = {"X-CSRFToken": token}

# 1. Create a claim
create_claim = session.post("https://skinsurance.tech/api/claims", json={
    "claim_no": "TEST-CLAIM-LIVE-01",
    "policy_no": "POL-LIVE-01",
    "insured_name": "TEST INSURED LIVE",
    "vehicle_no": "WB-99-LIVE",
    "insurer": "National Insurance Co. Ltd.",
    "survey_type": "final",
    "status": "new_appointment"
}, headers=headers)
print("Create claim response:", create_claim.status_code, create_claim.json())
rep_id = create_claim.json().get("report_id")

# 2. Query claims without filter
all_claims = session.get("https://skinsurance.tech/api/claims")
print("All claims count:", all_claims.json().get("total"), [c.get("claim_no") for c in all_claims.json().get("items", [])])

# 3. Query claim by ID
if rep_id:
    get_claim = session.get(f"https://skinsurance.tech/api/reports/{rep_id}")
    print("Get report by ID:", get_claim.status_code)