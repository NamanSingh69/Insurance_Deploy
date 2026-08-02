"""
Unit tests for new client enhancements:
- Convenience (Route, KM, Rate/KM) and Photocopy charges in Fee Bills.
- Gmail intimation cancellation.
- Dynamic pending documents checklist.
- 7-day 3-cycle document pending reminders.
"""
import json
import pytest
from unittest.mock import MagicMock, patch

def test_fee_bill_convenience_and_photocopy(authenticated_client, mock_sheets_db):
    """Test saving and retrieving fee bills with convenience breakdown and photocopy charges."""
    payload = {
        "invoice_no": "NIC/AUG-26/01",
        "invoice_date": "2026-08-02",
        "insurer_name": "National Insurance Company",
        "insured_name": "Sk Anowar Ali Client Test",
        "policy_no": "POL9999",
        "claim_no": "CLM8888",
        "vehicle_no": "WB10AB1234",
        "professional_fee": 1500.0,
        "convenience_route": "Krishnanagar to Kolkata",
        "convenience_km": 200.0,
        "convenience_rate": 10.0,
        "conveyance_fee": 2000.0,
        "photocopy_amount": 150.0,
        "taxable_amount": 3650.0,  # 1500 + 2000 + 150
        "gst_pc": 18.0,
        "gst_amount": 657.0,
        "gross_invoice_value": 4307.0,
        "total_amount": 4307.0
    }

    mock_sheets_db.save_fee_bill.return_value = "fb-conv-123"
    mock_sheets_db.get_workspace_fee_bills.return_value = [payload]

    # POST fee bill
    res_post = authenticated_client.post('/api/fee_bills', json=payload)
    assert res_post.status_code in [200, 201]

    # GET fee bills
    res_get = authenticated_client.get('/api/fee_bills')
    assert res_get.status_code == 200
    bills = res_get.get_json()
    assert len(bills) >= 1
    bill = bills[0]
    assert bill["convenience_route"] == "Krishnanagar to Kolkata"
    assert bill["convenience_km"] == 200.0
    assert bill["conveyance_fee"] == 2000.0
    assert bill["photocopy_amount"] == 150.0


def test_gmail_intimation_cancellation(authenticated_client, mock_sheets_db):
    """Test cancelling a Gmail intimation."""
    mock_sheets_db.cancel_gmail_sync_message.return_value = True

    res = authenticated_client.post('/api/gmail/intimation/msg-12345/cancel')
    assert res.status_code == 200
    data = res.get_json()
    assert data.get('success') is True
    mock_sheets_db.cancel_gmail_sync_message.assert_called_with('msg-12345')


def test_get_and_add_pending_gmail_intimation(authenticated_client, mock_sheets_db):
    """Test fetching pending Gmail intimations list and adding an intimation card to Claim Register."""
    pending_record = {
        'gmail_message_id': 'msg-appointment-99',
        'sender_email': 'claims@sbigeneral.in',
        'subject': 'SBI General: Survey Appointment Claim No MVO4078533',
        'received_at': '2026-08-02T12:00:00',
        'parse_data_json': json.dumps({
            'claim_no': 'MVO4078533',
            'policy_no': 'POL-SBI-99',
            'insurer': 'SBI General Insurance Co. Ltd.',
            'insured_name': 'Rahul Verma',
            'contact': '9876543210',
            'vehicle_no': 'WB-23-C-8999',
            'snippet': 'Survey report assigned against claim No MVO4078533'
        }),
        'sync_status': 'pending'
    }

    mock_sheets_db.get_pending_gmail_messages.return_value = [pending_record]
    mock_sheets_db.get_gmail_sync_message.return_value = pending_record
    mock_sheets_db.find_workspace_report_by_claim_no.return_value = None
    mock_sheets_db.reserve_report_number.return_value = 1
    mock_sheets_db.save_workspace_report.return_value = 'rep-added-99'

    # GET pending intimations list
    res_get = authenticated_client.get('/api/gmail/intimations')
    assert res_get.status_code == 200
    intimations = res_get.get_json().get('intimations', [])
    assert len(intimations) == 1
    assert intimations[0]['gmail_message_id'] == 'msg-appointment-99'

    # POST add intimation card to register
    res_add = authenticated_client.post('/api/gmail/intimation/msg-appointment-99/add')
    assert res_add.status_code == 200
    add_data = res_add.get_json()
    assert add_data.get('success') is True
    assert add_data.get('claim_no') == 'MVO4078533'
    assert add_data.get('action') == 'created'



def test_pending_documents_checklist_api(authenticated_client, mock_sheets_db):
    """Test GET and POST pending documents checklist per claim."""
    sample_report = {
        'id': 'rep-claim-1',
        'saved_at': '2026-08-02T10:00:00',
        'status': 'documents_awaited',
        'claim_no': 'CLM777',
        'report_data_json': json.dumps({
            'survey_report': {'insured': 'Test Customer', 'claim_no': 'CLM777'},
            'pending_documents': [
                {'name': 'Claim Form', 'received': True},
                {'name': 'Fitness Certificate (Custom)', 'received': False}
            ]
        })
    }

    mock_sheets_db.get_report_by_id.return_value = sample_report
    mock_sheets_db.get_claim_reminder.return_value = {'reminder_count': 1, 'last_sent_at': '2026-08-01T10:00:00'}

    # GET checklist
    res_get = authenticated_client.get('/api/claims/rep-claim-1/pending_documents')
    assert res_get.status_code == 200
    data = res_get.get_json()
    assert 'pending_documents' in data
    assert len(data['pending_documents']) == 2
    assert data['pending_documents'][1]['name'] == 'Fitness Certificate (Custom)'

    # POST checklist update
    new_checklist = [
        {'name': 'Claim Form', 'received': True},
        {'name': 'RC Copy', 'received': True},
        {'name': 'Fitness Certificate (Custom)', 'received': True}
    ]
    res_post = authenticated_client.post('/api/claims/rep-claim-1/pending_documents', json={'pending_documents': new_checklist})
    assert res_post.status_code == 200
    assert res_post.get_json()['success'] is True


def test_pending_documents_reminders_cap(authenticated_client, mock_sheets_db):
    """Test 1st, 2nd, 3rd reminders and enforcement of 3-reminder maximum cap."""
    sample_report = {
        'id': 'rep-claim-reminder',
        'claim_no': 'CLM-REM-1',
        'insured_name': 'Rahul Roy',
        'vehicle_no': 'WB04A5555',
        'policy_no': 'POL1111',
        'insurer': 'SBI General Insurance Co. Ltd.',
        'status': 'documents_awaited',
        'report_data_json': json.dumps({
            'survey_report': {
                'insured': 'Rahul Roy',
                'claim_no': 'CLM-REM-1',
                'vehicle_regn_no': 'WB04A5555',
                'policy_no': 'POL1111',
                'insurer': 'SBI General Insurance Co. Ltd.'
            },
            'pending_documents': [
                {'name': 'Policy copy', 'received': False},
                {'name': 'Clear bank details', 'received': False}
            ]
        })
    }

    mock_sheets_db.get_report_by_id.return_value = sample_report

    # Reminder 1
    mock_sheets_db.get_claim_reminder.return_value = {'reminder_count': 0}
    res1 = authenticated_client.post('/api/claims/rep-claim-reminder/send_reminder', json={'claim_manager_email': 'manager@insurer.com'})
    assert res1.status_code == 200
    data1 = res1.get_json()
    assert data1['reminder_count'] == 1
    assert "any delay in submitting the required documents" in data1['message_text']

    # Reminder 2
    mock_sheets_db.get_claim_reminder.return_value = {'reminder_count': 1}
    res2 = authenticated_client.post('/api/claims/rep-claim-reminder/send_reminder', json={})
    assert res2.status_code == 200
    data2 = res2.get_json()
    assert data2['reminder_count'] == 2
    assert "second time reminder" in data2['message_text']

    # Reminder 3
    mock_sheets_db.get_claim_reminder.return_value = {'reminder_count': 2}
    res3 = authenticated_client.post('/api/claims/rep-claim-reminder/send_reminder', json={})
    assert res3.status_code == 200
    data3 = res3.get_json()
    assert data3['reminder_count'] == 3
    assert "third time reminder" in data3['message_text']

    # Reminder 4 (Exceeding max 3) -> should fail
    mock_sheets_db.get_claim_reminder.return_value = {'reminder_count': 3}
    res4 = authenticated_client.post('/api/claims/rep-claim-reminder/send_reminder', json={})
    assert res4.status_code == 400
    assert "Maximum 3 reminders" in res4.get_json()['error']
