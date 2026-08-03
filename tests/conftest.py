"""
Shared pytest fixtures for Insurance Report application tests.
"""
import os
import sys
import pytest
from unittest.mock import MagicMock, patch, PropertyMock

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set required environment variables before importing app
os.environ.setdefault("GEMINI_API_KEY", "test_api_key")
os.environ.setdefault("FLASK_SECRET_KEY", "test_secret_key_for_automated_tests")
os.environ.setdefault("TESTING", "1")  # Allows SECRET_KEY fallback in test mode
os.environ.setdefault("GOOGLE_SHEETS_CREDENTIALS", '{"type": "service_account", "project_id": "test"}')
os.environ.setdefault("GOOGLE_SHEET_NAME", "TestDB")
os.environ.setdefault("GOOGLE_DRIVE_FOLDER_ID", "test_folder_id")


# Patch external dependencies before importing app
@pytest.fixture(scope="session", autouse=True)
def mock_external_services():
    """Mock external services at session level."""
    with patch('google.generativeai.configure'), \
         patch('google.generativeai.GenerativeModel') as mock_model, \
         patch('google.genai.Client') as mock_genai_client:
        mock_instance = MagicMock()
        mock_model.return_value = mock_instance
        yield


@pytest.fixture
def mock_sheets_db():
    """Mock the sheets_db module."""
    mock_db = MagicMock()
    mock_db.connect = MagicMock()
    mock_db.get_user_by_username = MagicMock(return_value=None)
    mock_db.get_user_by_id = MagicMock(return_value=None)
    mock_db.save_report = MagicMock(return_value="test-report-id")
    mock_db.get_user_reports = MagicMock(return_value=[])
    mock_db.get_user_reports_metadata_only = MagicMock(return_value=[])
    mock_db.get_user_reports_page = MagicMock(return_value={
        'items': [],
        'page': 1,
        'page_size': 50,
        'total': 0
    })
    mock_db.get_workspace_reports_page = MagicMock(return_value={
        'items': [], 'page': 1, 'page_size': 50, 'total': 0
    })
    mock_db.get_accessible_reports_page = MagicMock(return_value={
        'items': [], 'page': 1, 'page_size': 50, 'total': 0
    })
    mock_db.get_workspace_report_by_id = MagicMock(return_value=None)
    mock_db.get_accessible_report_by_id = MagicMock(return_value=None)
    mock_db.find_workspace_report_by_claim_no = MagicMock(return_value=None)
    mock_db.reserve_report_number = MagicMock(return_value=1)
    mock_db.save_workspace_report = MagicMock(return_value='workspace-report-id')
    mock_db.update_workspace_report_status = MagicMock(return_value=True)
    mock_db.delete_workspace_report = MagicMock(return_value=True)
    mock_db.get_workspace_dashboard = MagicMock(return_value={
        'total_claims': 0, 'pending_claims': 0, 'completed_claims': 0,
        'new_appointment': 0, 'inspection_pending': 0, 'documents_awaited': 0,
        'report_under_preparation': 0, 'report_submitted': 0, 'closed': 0,
        'total_invoiced': 0, 'amount_received': 0, 'outstanding_fees': 0, 'overdue_count': 0,
    })
    mock_db.get_workspace_fee_bills = MagicMock(return_value=[])
    mock_db.get_gmail_sender_domains = MagicMock(return_value=[])
    mock_db.get_gmail_integration = MagicMock(return_value=None)
    mock_db.get_gmail_sync_message = MagicMock(return_value=None)
    mock_db.record_gmail_sync_message = MagicMock(return_value=True)
    mock_db.save_gmail_integration = MagicMock(return_value=True)
    mock_db.delete_gmail_integration = MagicMock(return_value=True)
    mock_db.get_admin_user = MagicMock(return_value=None)
    mock_db.list_admin_users = MagicMock(return_value=[])
    mock_db.set_user_locked = MagicMock(return_value=True)
    mock_db.reset_user_password = MagicMock(return_value=True)
    mock_db.update_user_permissions = MagicMock(return_value=True)
    mock_db.change_user_password = MagicMock(return_value=True)
    mock_db.create_user = MagicMock(return_value=2)
    mock_db.save_fee_bill = MagicMock(return_value='fee-bill-id')
    mock_db.get_job_by_request_id = MagicMock(return_value=None)
    mock_db.delete_report = MagicMock(return_value=True)
    mock_db.upload_image_to_drive = MagicMock(return_value={
        'id': 'drive-file-id',
        'view_link': 'https://drive.google.com/view',
        'download_link': 'https://drive.google.com/download'
    })
    # Modern private asset, job, drive, and credential helpers
    def _mock_create_asset(user_id=None, storage_kind=None, storage_locator=None, *args, **kwargs):
        return {
            'id': 'mock-asset-id',
            'user_id': user_id or '1',
            'storage_kind': storage_kind or 'private_local',
            'storage_locator': storage_locator or 'mock_locator.png',
            'original_name': kwargs.get('filename', 'test.png'),
            'mime_type': kwargs.get('mime_type', 'image/png'),
            'purpose': kwargs.get('purpose', 'photo'),
            'size_bytes': kwargs.get('size_bytes', 100),
            'checksum_sha256': kwargs.get('checksum_sha256', 'mockhash')
        }
    mock_db.create_asset = MagicMock(side_effect=_mock_create_asset)

    mock_db.get_asset_for_access = MagicMock(return_value={
        'id': 'mock-asset-id',
        'user_id': '1',
        'storage_path': 'mock_storage_path.png',
        'mime_type': 'image/png',
        'original_name': 'test.png',
        'purpose': 'signature',
        'size_bytes': 100
    })

    def _mock_create_job(user_id, kind, payload=None):
        return {
            'id': 'mock-job-id',
            'user_id': user_id,
            'kind': kind,
            'status': 'queued',
            'payload': payload
        }
    mock_db.create_job = MagicMock(side_effect=_mock_create_job)

    mock_db.get_job_for_user = MagicMock(return_value={
        'id': 'mock-job-id',
        'user_id': '1',
        'status': 'completed',
        'job_type': 'generate_files',
        'input_asset_ids': [],
        'result_asset_ids': ['mock-asset-id'],
        'error_message': None
    })
    mock_db.attach_assets_to_report = MagicMock(return_value=True)
    mock_db.set_user_signature_asset = MagicMock(return_value=True)
    mock_db.get_users_for_credential_migration = MagicMock(return_value=[])
    mock_db.update_user_encrypted_gemini_key = MagicMock(return_value=True)
    mock_db.save_drive_integration = MagicMock(return_value=True)
    mock_db.get_drive_integration = MagicMock(return_value=None)
    mock_db.delete_drive_integration = MagicMock(return_value=True)
    return mock_db


@pytest.fixture
def app(mock_sheets_db, tmp_path):
    """Create Flask test application with mocked dependencies and private storage."""
    from app import create_app
    private_dir = str(tmp_path / "private_assets")
    os.makedirs(private_dir, exist_ok=True)
    flask_app = create_app(
        db_adapter=mock_sheets_db,
        task_executor=MagicMock(),
        config={
            'TESTING': True,
            'WTF_CSRF_ENABLED': False,
            'LOGIN_DISABLED': False,
            'PRIVATE_STORAGE_DIR': private_dir,
        }
    )
    yield flask_app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def mock_user():
    """Create a mock user dict."""
    return {
        'id': '1',
        'username': 'testuser',
        'password_hash': '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.HJtF/OqJkKxhTu',  # 'password123'
        'full_name': 'Test User',
        'qualifications': 'B.E.',
        'designation': 'Surveyor',
        'license_no': 'LIC123',
        'expiry_date': '2025-12-31',
        'membership_no': 'MEM123',
        'address_line_1': 'Address 1',
        'address_line_2': 'Address 2',
        'address_line_3': 'City, State',
        'contact_no': '9876543210',
        'email': 'test@example.com',
        'role': 'admin',
        'admin_id': None,
        'is_locked': False,
        'permissions': {},
        'must_change_password': False,
        'encrypted_gemini_api_key': None,
        'signature_asset_id': 'mock-sig-asset-id',
    }


@pytest.fixture
def authenticated_client(app, mock_sheets_db, mock_user):
    """Create authenticated test client."""
    mock_sheets_db.get_user_by_username.return_value = mock_user
    mock_sheets_db.get_user_by_id.return_value = mock_user
    
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['_user_id'] = '1'
            sess['_fresh'] = True
        yield client


@pytest.fixture
def sample_survey_data():
    """Sample survey report data for testing."""
    return {
        "report_no": "SR-2026-001",
        "report_date": "2026-01-29",
        "policy_no": "POL-123456",
        "claim_no": "CLM-789",
        "policy_validity": "2025-01-01 to 2026-01-01",
        "insurer": "Test Insurance Company",
        "insured": "Test Insured Name",
        "insured_contact_name": "John Doe",
        "insured_contact_no": "9876543210",
        "vehicle_regn_no": "WB-01-AB-1234",
        "vehicle_make_model": "Maruti Swift",
        "vehicle_chassis_no": "CHASSIS123",
        "vehicle_engine_no": "ENGINE456"
    }


@pytest.fixture
def sample_assessment_data():
    """Sample assessment data for testing."""
    return {
        "header_gst": "19ABCDE1234F1Z5",
        "header_vehicle_year": "3",
        "policy_type": "NORMAL",
        "report_type": "Final Survey Report",
        "claim_type": "Cashless",
        "parts": [
            {
                "sl_no": 1,
                "part_name": "Bumper Front",
                "qty": 1,
                "part_amt": 5000,
                "type_part": "P",
                "gst_applicable": True,
                "original_gst_pc": 28
            }
        ],
        "user_labour_rows": [
            {
                "part_name": "Bumper Work",
                "removing_refitting": 500,
                "denting_repairing": 1000,
                "painting": 2000
            }
        ],
        "salvage": 0,
        "deductibles": 1000
    }


@pytest.fixture
def sample_report_data(sample_survey_data, sample_assessment_data):
    """Complete sample report data."""
    return {
        "survey_report": sample_survey_data,
        "assessment": sample_assessment_data,
        "photos": {
            "first_inspection": {"images": [], "per_page": 4},
            "dismantling": {"images": [], "per_page": 4},
            "reinspection": {"images": [], "per_page": 4}
        }
    }
