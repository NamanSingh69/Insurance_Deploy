import requests
import time

s = requests.Session()
BASE_URL = "http://localhost:5000"

print("--- Testing Database Integration ---")
start = time.time()
r = s.get(BASE_URL + "/login")
csrf_time = time.time() - start
print(f"GET /login (Load page & CSRF) latency: {csrf_time:.4f}s")
print(f"Status: {r.status_code}")

print("\n--- Testing Authentication ---")
login_data = {"username": "NAMAN", "password": "69"} # Ensure NAMAN is created or existing username here, wait, old user is NAMAN with pass 69420
login_data = {"username": "NAMAN", "password": "69420"}
start = time.time()
r = s.post(BASE_URL + "/login", data=login_data)
login_time = time.time() - start
print(f"POST /login latency: {login_time:.4f}s")
print(f"Status: {r.status_code}")

print("\n--- Testing High-Volume Database Fetch ---")
start = time.time()
r = s.get(BASE_URL + "/api/reports") # If this exists or index page
fetch_time = time.time() - start
print(f"GET /api/reports via Postgres logic latency: {fetch_time:.4f}s")
print(f"Status: {r.status_code}")
