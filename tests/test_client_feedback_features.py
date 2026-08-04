import pytest
import json

def _auth(client, mock_sheets_db, role='admin'):
    user = {
        'id': '1' if role == 'admin' else '2',
        'username': 'admin' if role == 'admin' else 'emp',
        'role': role,
        'admin_id': 1,
        'permissions': {'gmail_sync': True},
        'is_locked': False,
        'must_change_password': False
    }
    mock_sheets_db.get_user_by_id.return_value = user
    with client.session_transaction() as sess:
        sess['_user_id'] = str(user['id'])
        sess['_fresh'] = True


def test_insurer_master_crud_and_auto_fill(client, mock_sheets_db):
    """Test creating, fetching, and auto-numbering via Insurer Master APIs."""
    _auth(client, mock_sheets_db, role='admin')

    mock_sheets_db.get_insurer_masters.return_value = [
        {
            'id': 1,
            'insurer_name': 'New India Assurance',
            'branch_name': 'Kolkata DO 1',
            'branch_address': '4 Mango Lane, Kolkata',
            'gstin': '19AABCN1234F1Z1',
            'invoice_prefix': 'NIA',
            'default_conveyance_rate': 10.0
        }
    ]
    mock_sheets_db.save_insurer_master.return_value = 1
    mock_sheets_db.get_next_insurer_invoice_number.return_value = 'NIA-1'

    # GET /api/insurers
    res = client.get('/api/insurers')
    assert res.status_code == 200
    data = res.get_json()
    assert data['success'] is True
    assert len(data['insurers']) == 1
    assert data['insurers'][0]['invoice_prefix'] == 'NIA'

    # GET /api/insurers/next-invoice-no
    res_no = client.get('/api/insurers/next-invoice-no?prefix=NIA')
    assert res_no.status_code == 200
    no_data = res_no.get_json()
    assert no_data['success'] is True
    assert no_data['next_invoice_no'] == 'NIA-1'


def test_gmail_staging_review_flow(client, mock_sheets_db):
    """Test fetching, accepting, and rejecting staged Gmail intimations."""
    _auth(client, mock_sheets_db, role='admin')

    mock_sheets_db.get_staged_gmail_intimations.return_value = [
        {
            'id': 10,
            'gmail_message_id': 'msg12345',
            'sender_email': 'oicl@orientalinsurance.co.in',
            'subject': 'New Claim Intimation: WB02A1234',
            'extracted_claim_no': 'OIC/2026/987',
            'extracted_insured_name': 'Rahul Sharma',
            'extracted_vehicle_no': 'WB02A1234',
            'extracted_policy_no': 'POL123456',
            'extracted_insurer_name': 'Oriental Insurance',
            'status': 'pending'
        }
    ]
    mock_sheets_db.update_staged_gmail_intimation_status.return_value = True

    # GET /api/gmail/staged
    res = client.get('/api/gmail/staged?status=pending')
    assert res.status_code == 200
    data = res.get_json()
    assert data['success'] is True
    assert len(data['intimations']) == 1

    # POST /api/gmail/staged/10/accept
    res_accept = client.post('/api/gmail/staged/10/accept')
    assert res_accept.status_code == 200
    assert res_accept.get_json()['success'] is True

    # POST /api/gmail/staged/10/reject
    res_reject = client.post('/api/gmail/staged/10/reject')
    assert res_reject.status_code == 200
    assert res_reject.get_json()['success'] is True


def test_claim_registration_new_contact_fields(client, mock_sheets_db):
    """Test claim creation with insured email and claim manager email fields."""
    _auth(client, mock_sheets_db, role='admin')

    mock_sheets_db.save_workspace_report.return_value = 'workspace-report-uuid'
    mock_sheets_db.reserve_report_number.return_value = 1

    payload = {
        'claim_no': 'CLM-2026-001',
        'insured_name': 'Anowar Ali',
        'insured_contact_no': '9876543210',
        'insured_email': 'anowar@example.com',
        'claim_manager_email': 'cm@insurer.com',
        'claim_manager_phone': '9123456789',
        'vehicle_no': 'WB04B5678',
        'vehicle_type': 'Private Car',
        'policy_no': 'POL-999',
        'insurer': 'New India Assurance'
    }

    res = client.post('/api/claims', json=payload)
    assert res.status_code == 201
    data = res.get_json()
    assert data['success'] is True
    assert data['report_id'] == 'workspace-report-uuid'

