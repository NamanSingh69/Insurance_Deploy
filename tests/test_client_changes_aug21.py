import json
import pytest
from unittest.mock import MagicMock, patch
from flask import session


def test_r1_fee_bill_edit_and_update(authenticated_client, mock_sheets_db):
    """R1: Test that saving an existing fee bill (with ID) updates the record without duplicating."""
    mock_sheets_db.save_fee_bill.return_value = "bill-101"
    mock_sheets_db.get_fee_bills.return_value = [
        {
            "id": "bill-101",
            "invoice_no": "UIC-1",
            "invoice_date": "2026-08-20",
            "insurer_name": "United India Insurance Co.",
            "insurer_gst": "19AAACU5055K1ZX",
            "surveyor_code": "2075995",
            "insured_name": "PINAKI SAHA",
            "vehicle_no": "WB-95-A-7632",
            "claim_no": "3126240110",
            "policy_no": "060088312000101NC077",
            "professional_fee": 2000.0,
            "conveyance_charges": 750.0,
            "taxable_amount": 2750.0,
            "gst_amount": 495.0,
            "gross_invoice_value": 3245.0,
            "payment_status": "unpaid",
            "invoice_status": "draft",
        }
    ]

    # Save edit with existing ID
    payload = {
        "id": "bill-101",
        "invoice_no": "UIC-1",
        "invoice_date": "2026-08-21",
        "insurer_name": "United India Insurance Co.",
        "insurer_gst": "19AAACU5055K1ZX",
        "surveyor_code": "2075995",
        "insured_name": "PINAKI SAHA",
        "vehicle_no": "WB-95-A-7632",
        "claim_no": "3126240110",
        "professional_fee": 2500.0,
        "conveyance_charges": 750.0,
        "taxable_amount": 3250.0,
        "gst_amount": 585.0,
        "gross_invoice_value": 3835.0,
        "payment_status": "unpaid",
    }
    res = authenticated_client.post('/api/fee_bills', json=payload)
    assert res.status_code == 201
    data = res.get_json()
    assert data['success'] is True
    assert data['id'] == "bill-101"
    mock_sheets_db.save_fee_bill.assert_called()


def test_r2_employee_can_delete_workspace_insurer_master(client, mock_sheets_db):
    """R2: Verify that employees can delete insurer masters belonging to their workspace."""
    mock_sheets_db.get_user_by_id.return_value = {
        'id': 1,
        'username': 'USER',
        'role': 'employee',
        'workspace_admin_id': 3,
        'admin_id': 3,
        'is_locked': False,
    }
    mock_sheets_db.get_insurer_master_by_id.return_value = {
        'id': 15,
        'workspace_admin_id': 3,
        'insurer_name': 'United India Insurance Co.',
        'branch_name': 'Kalyannagar',
    }
    mock_sheets_db.delete_insurer_master.return_value = True

    with client.session_transaction() as sess:
        sess['_user_id'] = '1'

    res = client.delete('/api/insurers/15')
    assert res.status_code == 200
    assert res.get_json()['success'] is True
    mock_sheets_db.delete_insurer_master.assert_called_with(15, 3)


def test_r3_claim_creation_and_workspace_sharing(client, mock_sheets_db):
    """R3: Test full-field claim creation by employee and shared visibility."""
    mock_sheets_db.get_user_by_id.return_value = {
        'id': 1,
        'username': 'USER',
        'role': 'employee',
        'workspace_admin_id': 3,
        'admin_id': 3,
        'is_locked': False,
    }
    mock_sheets_db.reserve_report_number.return_value = 5
    mock_sheets_db.save_workspace_report.return_value = "rep-claim-uuid-99"

    with client.session_transaction() as sess:
        sess['_user_id'] = '1'

    payload = {
        'claim_no': '060088312000101NC077',
        'policy_no': '060088312000101',
        'insured_name': 'PINAKI SAHA',
        'insured_contact_no': '7980744834',
        'insured_email': 'pinaki@example.com',
        'claim_manager_email': 'manager@newindia.co.in',
        'claim_manager_phone': '915-52-BD-2799',
        'vehicle_no': 'WB-52-BD-2799',
        'vehicle_type': 'Private Car',
        'insurer': 'The New India Assurance Co. Ltd.',
        'insurer_branch': 'Berhampore DO',
        'workshop_name': 'GEEKAY AUTO PVT LTD',
        'workshop_phone': '9876543210',
        'date_of_loss': '2026-08-20',
        'survey_type': 'final',
        'status': 'new_appointment',
    }
    res = client.post('/api/claims', json=payload)
    assert res.status_code == 201
    data = res.get_json()
    assert data['success'] is True
    assert 'report_no' in data
    mock_sheets_db.save_workspace_report.assert_called()


def test_r4_extract_intimation_endpoint(client, mock_sheets_db):
    """R4: Test /api/claims/extract_intimation endpoint with mocked AI extraction."""
    mock_sheets_db.get_user_by_id.return_value = {
        'id': 1,
        'username': 'USER',
        'role': 'employee',
        'workspace_admin_id': 3,
        'admin_id': 3,
        'is_locked': False,
    }
    with client.session_transaction() as sess:
        sess['_user_id'] = '1'

    extracted_mock = {
        'claim_no': '060088312000101NC077',
        'policy_no': '060088312000101',
        'insured_name': 'PINAKI SAHA',
        'insured_contact_no': '7980744834',
        'vehicle_no': 'WB-52-BD-2799',
        'vehicle_type': 'Private Car',
        'insurer': 'The New India Assurance Co. Ltd.',
        'insurer_branch': 'Berhampore DO',
        'workshop_name': 'GEEKAY AUTO PVT LTD',
        'date_of_loss': '2026-08-20',
        'survey_type': 'final',
    }

    with patch('modules.gemini.execute_intimation_extraction', return_value=extracted_mock):
        from io import BytesIO
        data = {'intimation_pdf': (BytesIO(b'%PDF-1.4 dummy intimation'), 'intimation.pdf')}
        res = client.post('/api/claims/extract_intimation', data=data, content_type='multipart/form-data')
        assert res.status_code == 200
        result = res.get_json()
        assert result['success'] is True
        assert result['data']['claim_no'] == '060088312000101NC077'
        assert result['data']['insured_name'] == 'PINAKI SAHA'


def test_r5_employee_gemini_key_resolution_hierarchy(mock_sheets_db, monkeypatch):
    """R5: Verify that an employee with no key inherits workspace admin's encrypted key."""
    from cryptography.fernet import Fernet
    test_fernet_key = Fernet.generate_key().decode()
    monkeypatch.setenv("CREDENTIAL_ENCRYPTION_KEY", test_fernet_key)

    from modules.credentials import resolve_gemini_api_key, encrypt_text
    
    # Employee user with no key
    employee_user = {
        'id': 1,
        'username': 'USER',
        'role': 'employee',
        'admin_id': 3,
        'workspace_admin_id': 3,
        'encrypted_gemini_api_key': None,
        'gemini_api_key': None,
    }
    
    # Admin user with encrypted key
    admin_user = {
        'id': 3,
        'username': 'SKANOWAR',
        'role': 'admin',
        'encrypted_gemini_api_key': encrypt_text('AIzaSyAdminKey12345'),
    }
    
    mock_sheets_db.get_user_by_id.side_effect = lambda uid: admin_user if uid == 3 else employee_user
    
    resolved_key = resolve_gemini_api_key(employee_user, db_adapter=mock_sheets_db)
    assert resolved_key == 'AIzaSyAdminKey12345'