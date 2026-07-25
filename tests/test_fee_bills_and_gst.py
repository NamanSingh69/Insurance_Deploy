"""
Unit and Integration tests for Standalone Fee Bills, Auto Invoice Numbering,
Signature Toggle, and 10-Column Monthly GST Excel Export.
"""
import io
import json
import pytest
from unittest.mock import MagicMock, patch


def test_get_next_invoice_number_format(app):
    """Test invoice number generation logic with company initials, month-year, and sequence."""
    from db import db
    
    # Test cases: Company Name, Date Str -> Expected Prefix format
    # National Insurance Company -> NIC/JUL-26/01
    inv_1 = db.get_next_invoice_number(user_id=1, insurer_name="National Insurance Company", date_str="2026-07-25")
    assert inv_1.startswith("NIC/JUL-26/")
    assert inv_1.endswith("01") or inv_1.endswith("001")

    # Oriental Insurance Company Limited -> OICL/JUL-26/01
    inv_2 = db.get_next_invoice_number(user_id=1, insurer_name="Oriental Insurance Company Limited", date_str="2026-07-25")
    assert inv_2.startswith("OICL/JUL-26/")


def test_api_next_invoice_no_endpoint(authenticated_client, mock_sheets_db):
    """Test GET /api/next_invoice_no route."""
    mock_sheets_db.get_next_invoice_number.return_value = "NIC/JUL-26/01"
    response = authenticated_client.get('/api/next_invoice_no?insurer=National+Insurance+Company&date=2026-07-25')
    assert response.status_code == 200
    data = response.get_json()
    assert data.get('invoice_no') == "NIC/JUL-26/01"


def test_standalone_fee_bill_crud(authenticated_client, mock_sheets_db):
    """Test saving and retrieving standalone fee bills."""
    fee_bill_payload = {
        "invoice_no": "NIC/JUL-26/01",
        "invoice_date": "2026-07-25",
        "insurer_name": "National Insurance Company",
        "insured_name": "John Doe",
        "policy_no": "POL12345",
        "claim_no": "CLM67890",
        "vehicle_no": "WB02AB1234",
        "taxable_amount": 1000.0,
        "gst_pc": 18.0,
        "gst_amount": 180.0,
        "total_amount": 1180.0
    }
    
    mock_sheets_db.save_fee_bill.return_value = "fb-12345"
    mock_sheets_db.get_user_fee_bills.return_value = [fee_bill_payload]

    # Save
    res_save = authenticated_client.post('/api/fee_bills', json=fee_bill_payload)
    assert res_save.status_code in [200, 201]

    # Get
    res_get = authenticated_client.get('/api/fee_bills')
    assert res_get.status_code == 200
    bills = res_get.get_json()
    assert len(bills) >= 1
    assert bills[0]["invoice_no"] == "NIC/JUL-26/01"


def test_download_gst_excel_10_columns(authenticated_client, mock_sheets_db):
    """Test /download_gst_excel produces CSV with the required 10 columns."""
    sample_report = {
        'id': 'rep-1',
        'saved_at': '2026-07-20T10:00:00',
        'report_data_json': json.dumps({
            'survey_report': {
                'insured': 'Rajesh Sharma',
                'policy_no': 'P9999',
                'claim_no': 'C8888',
                'vehicle_regn_no': 'WB11A1111',
                'report_no': 'NIC/JUL-26/01',
                'report_date': '20.07.2026'
            },
            'assessment': {
                'page3_details': {
                    'fee_items': [{'name': 'Final Survey Fees', 'amount': '1000.00'}]
                }
            }
        })
    }
    sample_fee_bill = {
        'id': 'fb-1',
        'created_at': '2026-07-22T11:00:00',
        'insured_name': 'Anita Roy',
        'policy_no': 'P7777',
        'claim_no': 'C6666',
        'vehicle_no': 'WB22B2222',
        'invoice_no': 'NIC/JUL-26/02',
        'invoice_date': '2026-07-22',
        'gst_pc': 18.0,
        'gst_amount': 180.0,
        'taxable_amount': 1000.0,
        'total_amount': 1180.0
    }

    mock_sheets_db.get_user_reports.return_value = [sample_report]
    mock_sheets_db.get_user_fee_bills.return_value = [sample_fee_bill]

    res = authenticated_client.get('/download_gst_excel?from_date=2026-07-01&to_date=2026-07-31')
    assert res.status_code == 200
    assert res.mimetype in ['text/csv', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'application/octet-stream']

    csv_content = res.data.decode('utf-8')
    lines = [line.strip() for line in csv_content.splitlines() if line.strip()]
    assert len(lines) >= 2  # Header + rows

    header = lines[0].split(',')
    expected_headers = [
        "Insured Name",
        "Policy number",
        "Claim number",
        "Vehicle number",
        "Invoice no",
        "Invoice date",
        "Gst %",
        "Gst amount",
        "Taxable amount",
        "Total amount (including GST)"
    ]
    # Check that all 10 column names are in header
    for h in expected_headers:
        assert h.lower() in [col.strip().strip('"').lower() for col in header]
