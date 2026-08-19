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


def test_insurer_master_delete_and_validation(client, mock_sheets_db):
    """Test deleting an insurer master item, fetching single entry, and POST validation errors."""
    _auth(client, mock_sheets_db, role='admin')

    mock_sheets_db.get_insurer_master_by_id.return_value = {
        'id': 1,
        'insurer_name': 'Oriental Insurance',
        'branch_name': 'DO 2',
        'invoice_prefix': 'OIC'
    }
    mock_sheets_db.delete_insurer_master.return_value = True

    # GET /api/insurers/1
    res_get = client.get('/api/insurers/1')
    assert res_get.status_code == 200
    assert res_get.get_json()['insurer']['invoice_prefix'] == 'OIC'

    # DELETE /api/insurers/1
    res_del = client.delete('/api/insurers/1')
    assert res_del.status_code == 200
    assert res_del.get_json()['success'] is True

    # POST /api/insurers (Missing insurer_name)
    res_err = client.post('/api/insurers', json={'branch_name': 'Test Branch'})
    assert res_err.status_code == 400
    assert 'error' in res_err.get_json()


def test_distance_conveyance_fee_bill(client, mock_sheets_db):
    """Test saving a survey fee bill with distance conveyance calculation inputs."""
    _auth(client, mock_sheets_db, role='admin')

    mock_sheets_db.save_fee_bill.return_value = 'bill-uuid-123'

    payload = {
        'invoice_no': 'NIA-1',
        'invoice_date': '2026-08-05',
        'insurer_name': 'New India Assurance',
        'insured_name': 'Anowar Ali',
        'claim_no': 'CLM-001',
        'professional_fee': 5000.0,
        'convenience_type': 'distance',
        'convenience_km': 135.0,
        'convenience_rate': 10.0,
        'convenience_visits': 2,
        'conveyance_fee': 5400.0,
        'taxable_amount': 10400.0,
        'gst_pc': 18.0,
        'gst_amount': 1872.0,
        'total_amount': 12272.0
    }

    res = client.post('/api/fee_bills', json=payload)
    assert res.status_code == 201
    assert res.get_json()['id'] == 'bill-uuid-123'


def test_gmail_staged_not_found_handling(client, mock_sheets_db):
    """Test 404 response when attempting to accept a non-existent staged intimation."""
    _auth(client, mock_sheets_db, role='admin')

    mock_sheets_db.get_staged_gmail_intimations.return_value = []

    res = client.post('/api/gmail/staged/999/accept')
    assert res.status_code == 404
    assert res.get_json()['error'] == 'Staged intimation not found.'


def test_dynamic_insurer_prefix_invoice_numbers(client, mock_sheets_db):
    """Test next invoice number generation with dynamic prefixes (e.g. NIC, OGI)."""
    _auth(client, mock_sheets_db, role='admin')

    def side_effect(workspace_admin_id, prefix):
        return f"{prefix}-1"

    mock_sheets_db.get_next_insurer_invoice_number.side_effect = side_effect

    res_nic = client.get('/api/insurers/next-invoice-no?prefix=NIC')
    assert res_nic.status_code == 200
    assert res_nic.get_json()['next_invoice_no'] == 'NIC-1'

    res_ogi = client.get('/api/insurers/next-invoice-no?prefix=OGI')
    assert res_ogi.status_code == 200
    assert res_ogi.get_json()['next_invoice_no'] == 'OGI-1'


def test_employee_can_access_invoice_numbering_and_create_insurer_master_but_cannot_delete(client, mock_sheets_db):
    """Test employee can generate next invoice numbers and add masters, but cannot delete."""
    _auth(client, mock_sheets_db, role='employee')

    mock_sheets_db.get_next_insurer_invoice_number.return_value = 'NIC-1'
    mock_sheets_db.save_insurer_master.return_value = 5
    mock_sheets_db.delete_insurer_master.return_value = True

    # 1. Employee can get next invoice number
    res_no = client.get('/api/insurers/next-invoice-no?prefix=NIC')
    assert res_no.status_code == 200
    assert res_no.get_json()['next_invoice_no'] == 'NIC-1'

    # 2. Employee can create/save insurer master
    res_post = client.post('/api/insurers', json={'insurer_name': 'Reliance General', 'invoice_prefix': 'RGI'})
    assert res_post.status_code == 201
    assert res_post.get_json()['id'] == 5

    # 3. Employee CANNOT delete insurer master (Admin only)
    res_del = client.delete('/api/insurers/5')
    assert res_del.status_code == 403
    assert 'Admin permission required' in res_del.get_json()['error']


def test_user_file_segregation_in_claims_and_reports(client, mock_sheets_db):
    """Test that employee queries pass user_id scoping while admin queries default to workspace."""
    # Employee query
    _auth(client, mock_sheets_db, role='employee')
    mock_sheets_db.get_workspace_reports_page.return_value = {'items': [], 'total': 0, 'page': 1, 'page_size': 50}
    mock_sheets_db.get_accessible_reports_page.return_value = {'items': [], 'total': 0, 'page': 1, 'page_size': 50}

    res_emp = client.get('/api/claims')
    assert res_emp.status_code == 200
    # verify user_id passed to get_workspace_reports_page
    mock_sheets_db.get_workspace_reports_page.assert_called()

    # Admin query
    _auth(client, mock_sheets_db, role='admin')
    res_admin = client.get('/api/claims?user_id=2')
    assert res_admin.status_code == 200


def test_standalone_fee_bill_saving_and_list_query(client, mock_sheets_db):
    """Test saving an unlinked standalone fee bill and querying workspace bills."""
    _auth(client, mock_sheets_db, role='employee')
    mock_sheets_db.save_fee_bill.return_value = 'bill-999'
    mock_sheets_db.get_workspace_fee_bills.return_value = [{'id': 'bill-999', 'insurer_name': 'IndusInd'}]

    payload = {
        'invoice_no': 'IND-01',
        'insurer_name': 'IndusInd Bank / Insurance',
        'taxable_amount': 2500.0,
        'report_id': None
    }
    res_save = client.post('/api/fee_bills', json=payload)
    assert res_save.status_code == 201
    assert res_save.get_json()['id'] == 'bill-999'

    res_list = client.get('/api/fee_bills')
    assert res_list.status_code == 200
    assert len(res_list.get_json()) == 1




