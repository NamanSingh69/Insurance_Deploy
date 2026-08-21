import requests
import re

session = requests.Session()
login_page = session.get("https://skinsurance.tech/login")
print("Login Page Status:", login_page.status_code)

csrf_match = re.search(r'name=["\']csrf_token["\']\s+value=["\']([^"\']+)["\']', login_page.text)
csrf_token = csrf_match.group(1) if csrf_match else None
print("Extracted CSRF token:", csrf_token is not None)

# Check login with USER
login_res = session.post("https://skinsurance.tech/login", data={
    "username": "USER",
    "password": "UH65A#DF",
    "csrf_token": csrf_token
}, allow_redirects=True)
print("Login result URL:", login_res.url)
print("Logged in as USER:", "USER" in login_res.text or "Welcome" in login_res.text)

# Check Fee Register API
fee_res = session.get("https://skinsurance.tech/api/fee_bills")
print("GET /api/fee_bills status:", fee_res.status_code, "Count:", len(fee_res.json()) if fee_res.ok else fee_res.text)

# Check Claim Register API
claim_res = session.get("https://skinsurance.tech/api/claims")
print("GET /api/claims status:", claim_res.status_code, "Total:", claim_res.json().get("total") if claim_res.ok else claim_res.text)

# Check Insurers API
ins_res = session.get("https://skinsurance.tech/api/insurers")
print("GET /api/insurers status:", ins_res.status_code, "Insurers count:", len(ins_res.json().get("insurers", [])) if ins_res.ok else ins_res.text)