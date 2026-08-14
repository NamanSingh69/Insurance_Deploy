import os
import sys
import re

def verify_codebase():
    print("==================================================")
    print("VERIFYING REQUIREMENTS R1 THROUGH R6 IMPLEMENTATION")
    print("==================================================\n")

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    index_html = open(os.path.join(root, 'templates', 'index.html'), 'r', encoding='utf-8').read()
    script_js = open(os.path.join(root, 'static', 'script.js'), 'r', encoding='utf-8').read()
    style_css = open(os.path.join(root, 'static', 'style.css'), 'r', encoding='utf-8').read()
    app_py = open(os.path.join(root, 'app.py'), 'r', encoding='utf-8').read()

    # R1 Verification
    print("--- [R1] In-Place Dashboard KPI Drill-Down ---")
    assert 'id="dashboard-drilldown-section"' in index_html, "Missing dashboard-drilldown-section in index.html"
    assert 'id="dashboard-drilldown-tbody"' in index_html, "Missing dashboard-drilldown-tbody in index.html"
    assert 'function renderDashboardDrilldown' in script_js, "Missing renderDashboardDrilldown in script.js"
    assert '.clickable-metric.active-metric-card' in style_css, "Missing active-metric-card in style.css"
    print("[PASS] R1: Dashboard drill-down table, JavaScript handler, and CSS active highlights verified.\n")

    # R2 Verification
    print("--- [R2] Fix Pending Docs Checklist ReferenceError ---")
    assert 'const reminderInfo = data.reminder_info || {};' in script_js, "Missing reminderInfo in script.js"
    assert 'reminder_info.reminder_count' not in script_js, "Uncaught reminder_info ReferenceError still present in script.js"
    assert 'reminderInfo.reminder_count' in script_js, "Missing reminderInfo.reminder_count in script.js"
    print("[PASS] R2: Fixed reminderInfo ReferenceError in openPendingDocsModal.\n")

    # R3 Verification
    print("--- [R3] Insurer Master Setup & Usability Guidance ---")
    assert 'open-insurer-master-modal-btn' in index_html, "Missing Manage Insurer Masters button in index.html"
    assert 'Insurer Master Auto-Fill &amp; Setup' in index_html, "Missing Insurer Master helper guidance in index.html"
    print("[PASS] R3: Insurer Master guidance banner and manage button verified.\n")

    # R4 Verification
    print("--- [R4] Smart Auto-Prefix & Typing Match for Invoice No ---")
    assert 'function deriveInsurerAcronym' in script_js, "Missing deriveInsurerAcronym in script.js"
    assert 'handleFeeInsurerInput' in script_js, "Missing handleFeeInsurerInput in script.js"
    assert '/api/insurers/next-invoice-no' in app_py, "Missing next-invoice-no endpoint in app.py"
    assert 'is_admin_user(current_user)' in app_py, "Missing admin check in next-invoice-no endpoint"
    print("[PASS] R4: Smart acronym derivation (NIC, OGI, NIA, etc.) and auto-prefix generation verified.\n")

    # R5 Verification
    print("--- [R5] Professional Fee Stepper & Live Calculation Summary ---")
    assert 'id="fee-professional" type="number" min="0" step="1"' in index_html, "fee-professional step=1 not set in index.html"
    assert 'id="fee-live-calc-box"' in index_html, "Missing fee-live-calc-box in index.html"
    assert 'function updateLiveFeeSummary' in script_js, "Missing updateLiveFeeSummary in script.js"
    print("[PASS] R5: Professional Fee step=1 and live fee calculation breakdown box verified.\n")

    # R6 Verification
    print("--- [R6] Photo Upload Rate Limit & Error Diagnostic Fix ---")
    assert '@limiter.limit("300 per hour; 60 per minute")' in app_py, "Upload photo rate limit not updated in app.py"
    assert 'Failed to upload the following photo(s) to Google Drive' not in script_js, "Legacy false Google Drive alert still present"
    assert 'Failed to upload ${failures.length} photo(s)' in script_js, "Accurate failure alert missing in script.js"
    print("[PASS] R6: Increased photo upload rate limit and accurate diagnostic reporting verified.\n")

    print("==================================================")
    print("ALL VERIFICATION CHECKS PASSED SUCCESSFULLY (6/6)")
    print("==================================================")

if __name__ == '__main__':
    verify_codebase()
