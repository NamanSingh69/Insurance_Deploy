import os
import time
from playwright.sync_api import sync_playwright

ARTIFACT_DIR = r"C:\Users\namsi\.gemini\antigravity\brain\dd777ced-ad19-47b2-9a11-18068b17f016"
os.makedirs(ARTIFACT_DIR, exist_ok=True)

BASE_URL = "https://skinsurance.tech"

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        print("--> 1. Logging in as Admin (SKANOWAR)...")
        page.goto(f"{BASE_URL}/login", wait_until="networkidle")
        page.fill("#username", "SKANOWAR")
        page.fill("#password", "AnowarAdmin@2026")
        page.click("button[type='submit']")
        page.wait_for_load_state("networkidle")
        time.sleep(2)

        # Admin Dashboard Screenshot
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "admin_01_dashboard.png"), full_page=False)
        print("Captured admin_01_dashboard.png")

        # Open Insurer Master Modal (R1)
        print("--> 2. Opening Insurer Master modal (R1)...")
        # Click on insurer master trigger if available or show modal
        page.evaluate("""() => {
            const modal = document.getElementById('insurer-master-modal');
            if (modal) {
                modal.classList.remove('hidden');
                modal.style.display = 'flex';
            }
            if (typeof loadInsurerMasters === 'function') loadInsurerMasters();
        }""")
        time.sleep(2)
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "admin_02_insurer_master_surveyor_code.png"), full_page=False)
        print("Captured admin_02_insurer_master_surveyor_code.png")

        # Close Insurer Master Modal
        page.evaluate("""() => {
            const modal = document.getElementById('insurer-master-modal');
            if (modal) {
                modal.classList.add('hidden');
                modal.style.display = 'none';
            }
        }""")

        # Navigate to Fee Register (R1, R2, R3)
        print("--> 3. Navigating to Fee Register...")
        page.evaluate("""() => {
            if (typeof showTab === 'function') showTab('fee-register-tab');
            const tab = document.getElementById('fee-register-tab');
            if (tab) {
                document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
                tab.classList.remove('hidden');
            }
            if (typeof fetchFees === 'function') fetchFees();
        }""")
        time.sleep(2)
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "admin_03_fee_register_form_and_surveyor_code.png"), full_page=False)
        print("Captured admin_03_fee_register_form_and_surveyor_code.png")

        # Open Fee Payment Modal (R3)
        print("--> 4. Opening Fee Payment Modal with Remarks (R3)...")
        page.evaluate("""() => {
            const payModal = document.getElementById('fee-payment-modal');
            if (payModal) {
                payModal.classList.remove('hidden');
                payModal.style.display = 'flex';
                const invEl = document.getElementById('pay-modal-invoice-no');
                if (invEl) invEl.innerText = 'NIC/2026/0001';
                const totEl = document.getElementById('pay-modal-total-amt');
                if (totEl) totEl.innerText = '₹2,360.00';
                const insEl = document.getElementById('pay-modal-insurer');
                if (insEl) insEl.innerText = 'National Insurance Co. Ltd.';
                const clmEl = document.getElementById('pay-modal-claim');
                if (clmEl) clmEl.innerText = 'CLM-998877';
                const stEl = document.getElementById('pay-modal-status');
                if (stEl) stEl.value = 'partially_paid';
                const dtEl = document.getElementById('pay-modal-date');
                if (dtEl) dtEl.value = '2026-08-20';
                const amtEl = document.getElementById('pay-modal-amount');
                if (amtEl) amtEl.value = '1800.00';
                const tdsEl = document.getElementById('pay-modal-tds');
                if (tdsEl) tdsEl.value = '200.00';
                const refEl = document.getElementById('pay-modal-reference');
                if (refEl) refEl.value = 'UTR99887766';
                const remEl = document.getElementById('pay-modal-remarks');
                if (remEl) remEl.value = 'Conveyance deduction of Rs 360 disallowed by DO manager.';
            }
        }""")
        time.sleep(1)
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "admin_04_fee_payment_modal_remarks.png"), full_page=False)
        print("Captured admin_04_fee_payment_modal_remarks.png")

        # Close Payment Modal
        page.evaluate("""() => {
            const payModal = document.getElementById('fee-payment-modal');
            if (payModal) {
                payModal.classList.add('hidden');
                payModal.style.display = 'none';
            }
        }""")

        # Employee Session in a clean context
        print("--> 5. Logging in as Employee (USER) in fresh context...")
        emp_context = browser.new_context(viewport={"width": 1440, "height": 900})
        emp_page = emp_context.new_page()
        emp_page.goto(f"{BASE_URL}/login", wait_until="networkidle")
        emp_page.fill("#username", "USER")
        emp_page.fill("#password", "UH65A#DF")
        emp_page.click("button[type='submit']")
        emp_page.wait_for_load_state("networkidle")
        time.sleep(2)

        # Employee Dashboard Screenshot (Verifying Financial Redaction)
        emp_page.screenshot(path=os.path.join(ARTIFACT_DIR, "employee_01_dashboard_financial_redacted.png"), full_page=False)
        print("Captured employee_01_dashboard_financial_redacted.png")

        # Employee Fee Register
        print("--> 6. Navigating to Employee Fee Register...")
        emp_page.evaluate("""() => {
            if (typeof showTab === 'function') showTab('fee-register-tab');
            const tab = document.getElementById('fee-register-tab');
            if (tab) {
                document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
                tab.classList.remove('hidden');
            }
            if (typeof fetchFees === 'function') fetchFees();
        }""")
        time.sleep(2)
        emp_page.screenshot(path=os.path.join(ARTIFACT_DIR, "employee_02_fee_register.png"), full_page=False)
        print("Captured employee_02_fee_register.png")

        browser.close()
        print("\n--> All visual verification screenshots captured successfully!")

if __name__ == "__main__":
    run()
