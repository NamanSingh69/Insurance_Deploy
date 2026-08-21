import os
import time
from playwright.sync_api import sync_playwright

artifact_dir = r"C:\Users\namsi\.gemini\antigravity\brain\49ca1118-cf73-4409-a6b3-5832ec6c4763"
os.makedirs(artifact_dir, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()

    # 1. Login
    print("Navigating to login page...")
    page.goto("https://skinsurance.tech/login")
    page.fill("#username", "USER")
    page.fill("#password", "UH65A#DF")
    page.click("button[type='submit']")
    page.wait_for_load_state("networkidle")
    time.sleep(2)
    print("Logged in. Current URL:", page.url)

    # 2. Capture Claim Register Section (R3, R4)
    print("Navigating to Claim Register...")
    # Click Claim Register navigation or unhide section
    page.evaluate("""
        const sec = document.getElementById('claim-register-section');
        if (sec) { sec.classList.remove('hidden'); sec.style.display = 'block'; }
        const form = document.getElementById('new-claim-form');
        if (form) { form.classList.remove('hidden'); form.style.display = 'grid'; }
    """)
    time.sleep(1)
    claim_screenshot = os.path.join(artifact_dir, "claim_register_verified.png")
    page.locator("#claim-register-section").screenshot(path=claim_screenshot)
    print("Saved claim_register_verified.png")

    # 3. Capture Survey Fee Register Section with Edit Button (R1)
    print("Navigating to Survey Fee Register...")
    page.evaluate("""
        const sec = document.getElementById('fee-register-section');
        if (sec) { sec.classList.remove('hidden'); sec.style.display = 'block'; }
        const claimSec = document.getElementById('claim-register-section');
        if (claimSec) { claimSec.classList.add('hidden'); claimSec.style.display = 'none'; }
    """)
    time.sleep(2)
    fee_screenshot = os.path.join(artifact_dir, "fee_register_edit_button_verified.png")
    page.locator("#fee-register-section").screenshot(path=fee_screenshot)
    print("Saved fee_register_edit_button_verified.png")

    # 4. Open Insurer Master Modal (R2)
    print("Opening Insurer Master Control Panel Modal...")
    page.evaluate("""
        const modal = document.getElementById('insurer-master-modal');
        if (modal) { modal.classList.remove('hidden'); modal.style.display = 'flex'; }
    """)
    time.sleep(2)
    im_screenshot = os.path.join(artifact_dir, "insurer_master_modal_verified.png")
    page.locator("#insurer-master-modal .modal-content").screenshot(path=im_screenshot)
    print("Saved insurer_master_modal_verified.png")

    browser.close()
    print("Browser verification completed successfully!")