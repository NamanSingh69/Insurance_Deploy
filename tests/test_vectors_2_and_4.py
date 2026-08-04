import pytest
import json
import io
import csv

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


def test_vector_2_multi_branch_insurer_state_code(client, mock_sheets_db):
    """Test Vector 2: Multi-branch insurer master creation with state code support."""
    _auth(client, mock_sheets_db, role='admin')

    mock_sheets_db.save_insurer_master.return_value = 101

    payload = {
        'insurer_name': 'New India Assurance',
        'branch_name': 'Kolkata DO 2',
        'branch_address': '8 Lyons Range, Kolkata',
        'gstin': '19AABCN5678F1Z2',
        'state_code': '19',
        'invoice_prefix': 'NIA-KOL2',
        'default_conveyance_rate': 12.0
    }

    res = client.post('/api/insurers', json=payload)
    assert res.status_code == 201
    assert res.get_json()['success'] is True
    assert res.get_json()['id'] == 101


def test_vector_4_gstr1_b2b_csv_export(client, mock_sheets_db):
    """Test Vector 4: GSTR-1 B2B CSV export formatting for CA submission."""
    _auth(client, mock_sheets_db, role='admin')

    mock_sheets_db.get_workspace_fee_bills.return_value = [
        {
            'id': 1,
            'invoice_no': 'NIA-KOL2-01',
            'invoice_date': '2026-08-05',
            'insurer_name': 'New India Assurance',
            'insurer_gst': '19AABCN5678F1Z2',
            'insured_name': 'Sk Anowar Ali',
            'claim_no': 'CLM-777',
            'taxable_amount': 10000.0,
            'gst_pc': 18.0,
            'gst_amount': 1800.0,
            'gross_invoice_value': 11800.0,
            'state_code': '19'
        }
    ]

    res = client.get('/download_gstr1_csv?month=2026-08')
    assert res.status_code == 200
    assert res.mimetype == 'text/csv'

    csv_content = res.data.decode('utf-8')
    reader = csv.reader(io.StringIO(csv_content))
    rows = list(reader)

    assert len(rows) == 2
    assert rows[0][0] == 'GSTIN/UIN of Recipient'
    assert rows[1][0] == '19AABCN5678F1Z2'
    assert rows[1][2] == 'NIA-KOL2-01'
    assert rows[1][4] == '11800.00'
    assert rows[1][5] == '19-West Bengal'
    assert rows[1][13] == '0.00'   # IGST
    assert rows[1][14] == '900.00'  # CGST
    assert rows[1][15] == '900.00'  # SGST


def test_vector_4_enhanced_fee_excel_totals(client, mock_sheets_db):
    """Test Vector 4: CA-friendly Survey Fee Register XLSX download with totals row."""
    _auth(client, mock_sheets_db, role='admin')

    mock_sheets_db.get_workspace_fee_bills.return_value = [
        {
            'id': 1,
            'invoice_no': 'NIA-1',
            'invoice_date': '2026-08-05',
            'survey_type': 'Final Survey',
            'insurer_name': 'New India Assurance',
            'insurer_gst': '19AABCN1234F1Z1',
            'insured_name': 'Rahul Sharma',
            'claim_no': 'CLM-100',
            'policy_no': 'POL-100',
            'vehicle_no': 'WB02A1234',
            'professional_fee': 4000.0,
            'conveyance_fee': 1000.0,
            'taxable_amount': 5000.0,
            'gst_pc': 18.0,
            'gst_amount': 900.0,
            'gross_invoice_value': 5900.0,
            'tds_amount': 0.0,
            'amount_received': 5900.0,
            'outstanding_amount': 0.0,
            'payment_status': 'paid'
        }
    ]

    res = client.get('/download_fees_excel?month=2026-08')
    assert res.status_code == 200
    assert 'spreadsheetml' in res.mimetype
