"""
VPS E2E Integration and Post-Deployment Test Suite.
Can run locally in process, or remotely against a live VPS target.
"""
import os
import time
import pytest
import requests

TARGET_URL = os.getenv("E2E_TARGET_URL")

@pytest.fixture
def e2e_session():
    """Create a logged-in session for remote testing, or return None for local mock testing."""
    if not TARGET_URL:
        yield None
        return

    session = requests.Session()
    # Read staging or production credentials from env
    username = os.getenv("E2E_TEST_USER", "USER")
    password = os.getenv("E2E_TEST_PASSWORD", "UH65A#DF")

    login_url = f"{TARGET_URL.rstrip('/')}/login?next=%2F"
    resp = session.post(login_url, data={
        "username": username,
        "password": password
    }, allow_redirects=True)

    if resp.status_code != 200 or "Login Successful!" not in resp.text:
        pytest.skip(f"Remote login not authenticated (status {resp.status_code})")

    yield session



def test_vps_endpoint_upload_flow(e2e_session, authenticated_client, mock_sheets_db):
    """Verify that old client-driven Gemini direct upload route returns 410 GONE."""
    if e2e_session:
        upload_url_endpoint = f"{TARGET_URL.rstrip('/')}/get_gemini_upload_url"
        resp = e2e_session.post(upload_url_endpoint, json={
            "filename": "e2e_test_doc.pdf",
            "mime_type": "application/pdf",
            "size": 1024
        })
        assert resp.status_code == 410, f"Expected 410 GONE, got: {resp.status_code}"
    else:
        response = authenticated_client.post('/get_gemini_upload_url', json={
            "filename": "e2e_test_doc.pdf",
            "mime_type": "application/pdf",
            "size": 1024
        })
        assert response.status_code == 410


def test_vps_async_processing_endpoints(e2e_session, authenticated_client, mock_sheets_db):
    """Test async document queue durable job status endpoint."""
    mock_sheets_db.get_job_for_user.return_value = {
        'id': 'task-123',
        'user_id': '1',
        'status': 'completed',
        'result': {'parts': []},
        'error': None
    }

    if e2e_session:
        # Remote status check
        status_url = f"{TARGET_URL.rstrip('/')}/process_pdf/status/nonexistent-task"
        resp = e2e_session.get(status_url)
        assert resp.status_code in [200, 404]
    else:
        # Local mock status assertion
        response = authenticated_client.get('/process_pdf/status/task-123')
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "completed"


def test_vps_download_ownership_security(e2e_session, authenticated_client, mock_sheets_db):
    """Verify that download endpoints reject download attempts for unowned files."""
    mock_sheets_db.get_job_by_request_id.return_value = {
        "id": "job-abc",
        "user_id": "999", # Other user
        "status": "completed"
    }

    if e2e_session:
        # Remote security check: trying to access standard file id
        download_url = f"{TARGET_URL.rstrip('/')}/download/report_pdf/unowned-req-id"
        resp = e2e_session.get(download_url)
        assert resp.status_code in [403, 404, 429]
    else:
        # Local mock security check
        response = authenticated_client.get('/download/report_pdf/req-abc')
        assert response.status_code in [403, 404]



# Helper imports for patching
from unittest.mock import MagicMock, patch
