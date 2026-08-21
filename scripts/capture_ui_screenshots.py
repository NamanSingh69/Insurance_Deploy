import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import time
import threading
from playwright.sync_api import sync_playwright

os.environ["RATELIMIT_STORAGE_URI"] = "memory://"
os.environ["FLASK_SECRET_KEY"] = "secret_key_test_screenshots"
os.environ["TESTING"] = "1"

from app import app
from db import db
from unittest.mock import MagicMock

brain_artifact_dir = r"C:\Users\namsi\.gemini\antigravity\brain\49ca1118-cf73-4409-a6b3-5832ec6c4763"
os.makedirs(brain_artifact_dir, exist_ok=True)

app.config['TESTING'] = True
app.config['WTF_CSRF_ENABLED'] = False

def run_flask():
    app.run(port=5005, debug=False, use_reloader=False)

t = threading.Thread(target=run_flask, daemon=True)
t.start()
time.sleep(2)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()

    # 1. Login as USER
    print("Navigating to login page...")
    page.goto("http://127.0.0.1:5005/login")
    page.fill("#username", "USER")
    page.fill("#password", "UH65A#DF")
    page.click("button[type='submit']")
    time.sleep(2)

    # 2. Capture Claim Register Section with Intimation PDF Upload (R3, R4)
    print("Rendering Claim Register with Intimation Upload...")
    page.evaluate("""
        const sec = document.getElementById('claim-register-section');
        if (sec) { sec.classList.remove('hidden'); sec.style.display = 'block'; }
        const form = document.getElementById('new-claim-form');
        if (form) { form.classList.remove('hidden'); form.style.display = 'grid'; }
    """)
    time.sleep(1)
    claim_path_1 = os.path.join(brain_artifact_dir, "claim_register_verified.png")
    page.locator("#claim-register-section").screenshot(path=claim_path_1)
    print("Saved claim_register_verified.png")

    # 3. Capture Survey Fee Register Section with Edit Button (R1)
    print("Rendering Survey Fee Register with Edit Button...")
    page.evaluate("""
        const sec = document.getElementById('fee-register-section');
        if (sec) { sec.classList.remove('hidden'); sec.style.display = 'block'; }
        const claimSec = document.getElementById('claim-register-section');
        if (claimSec) { claimSec.classList.add('hidden'); claimSec.style.display = 'none'; }
    """)
    time.sleep(1)
    fee_path_1 = os.path.join(brain_artifact_dir, "fee_register_edit_button_verified.png")
    page.locator("#fee-register-section").screenshot(path=fee_path_1)
    print("Saved fee_register_edit_button_verified.png")

    # 4. Open Insurer Master Modal (R2)
    print("Rendering Insurer Master Control Panel Modal...")
    page.evaluate("""
        const modal = document.getElementById('insurer-master-modal');
        if (modal) { modal.classList.remove('hidden'); modal.style.display = 'flex'; }
    """)
    time.sleep(1)
    im_path_1 = os.path.join(brain_artifact_dir, "insurer_master_modal_verified.png")
    page.locator("#insurer-master-modal .modal-content").screenshot(path=im_path_1)
    print("Saved insurer_master_modal_verified.png")

    browser.close()
    print("UI Visual Evidence captured successfully!")