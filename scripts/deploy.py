#!/usr/bin/env python3
"""
Automated 1-Click Deployment Script for Motor Survey Report Generator
Usage from your local computer terminal:
    python scripts/deploy.py
"""

import subprocess
import requests
import hmac
import hashlib
import json
import time
import sys

BASE_URL = "https://skinsurance.tech"
WEBHOOK_SECRET = "surveyorportal-deploy-2026"

def run_cmd(cmd):
    print(f"--> {cmd}")
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Error ({res.returncode}): {res.stderr.strip()}")
    else:
        if res.stdout.strip():
            print(res.stdout.strip())
    return res.returncode == 0

def main():
    print("==================================================")
    print(">>> AUTOMATED 1-CLICK DEPLOYMENT TO PRODUCTION VPS")
    print(f"Target: {BASE_URL}")
    print("==================================================")

    # 1. Push latest code to GitHub
    print("\n[Step 1/3] Pushing latest commits to GitHub origin/main...")
    run_cmd("git push origin main")

    # 2. Trigger signed deployment webhook on production VPS
    print("\n[Step 2/3] Triggering secure deployment webhook on VPS...")
    payload = json.dumps({"ref": "refs/heads/main", "action": "push"}).encode("utf-8")
    signature = "sha256=" + hmac.new(WEBHOOK_SECRET.encode("utf-8"), payload, hashlib.sha256).hexdigest()

    headers = {
        "Content-Type": "application/json",
        "X-Hub-Signature-256": signature
    }

    try:
        resp = requests.post(f"{BASE_URL}/api/deploy-webhook", data=payload, headers=headers, timeout=30)
        print(f"Webhook Response: HTTP {resp.status_code} -> {resp.text.strip()}")
    except Exception as e:
        print(f"Webhook request failed: {e}")

    # 3. Poll liveness & health check
    print("\n[Step 3/3] Verifying production deployment health...")
    time.sleep(3)
    for attempt in range(1, 6):
        try:
            h_resp = requests.get(f"{BASE_URL}/healthz", timeout=10)
            if h_resp.status_code == 200:
                print(f"[PASS] Production is LIVE and Healthy! (HTTP 200 OK: {h_resp.json()})")
                print("==================================================")
                print(">>> DEPLOYMENT COMPLETE!")
                print("==================================================")
                return
        except Exception as e:
            print(f"Attempt {attempt}/5: waiting for server... ({e})")
            time.sleep(3)

    print("[WARN] Health check did not return 200 immediately. Please check server logs.")

if __name__ == "__main__":
    main()
