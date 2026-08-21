import requests
import re

session = requests.Session()
login_page = session.get("https://skinsurance.tech/login")
csrf_token = re.search(r'name=["\']csrf_token["\']\s+value=["\']([^"\']+)["\']', login_page.text).group(1)

# Login as SKANOWAR
res = session.post("https://skinsurance.tech/login", data={
    "username": "SKANOWAR",
    "password": "UH65A#DF",
    "csrf_token": csrf_token
})

home_page = session.get("https://skinsurance.tech/")
token = re.search(r'<meta name="csrf-token" content="([^"]+)"', home_page.text).group(1)
headers = {"X-CSRFToken": token}

claims = session.get("https://skinsurance.tech/api/claims")
print("SKANOWAR claims status:", claims.status_code, "Total:", claims.json().get("total") if claims.ok else claims.text)

dash = session.get("https://skinsurance.tech/api/dashboard")
print("SKANOWAR dashboard:", dash.status_code, dash.json() if dash.ok else dash.text)