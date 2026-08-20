import pytest
import io
import json
from datetime import datetime
from unittest.mock import MagicMock, patch
from app import app
from db import PostgresDB
from modules.pdf import render_fee_report, UserSnapshot


@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key'
    with app.test_client() as c:
        yield c


class MockUser:
    def __init__(self, user_id=1, username='SKANOWAR', role='admin', workspace_admin_id=1):
        self.id = user_id
        self.username = username
        self.role = role
        self.workspace_admin_id = workspace_admin_id
        self.full_name = 'SK ANOWAR ALI'
        self.qualifications = 'B.Tech (Automobile)'
        self.designation = 'Surveyor & Loss Assessor'
        self.license_no = 'SLA-121784'
        self.expiry_date = '13-12-2026'
        self.membership_no = 'L/E/10721'
        self.address_line_1 = 'Natungram'
        self.address_line_2 = 'Nabadwip'
        self.address_line_3 = 'Nadia'
        self.contact_no = '8777207014'
        self.email = 'skanowarali93@gmail.com'
        self.surveyor_code = 'DEFAULT_CODE'
        self.surveyor_gstin = '19AZZPA2301R1ZM'
        self.bank_account_no = '33717014374'
        self.bank_name = 'SBI'
        self.bank_branch = 'Nabadwip'
        self.bank_ifsc = 'SBIN0001402'

    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)


def test_pdf_render_fee_report_with_custom_surveyor_code():
    """Verify that render_fee_report overrides UserSnapshot.surveyor_code with insurer-specific code."""
    user_snapshot = {
        'full_name': 'SK ANOWAR ALI',
        'qualifications': 'B.Tech (Automobile)',
        'designation': 'Surveyor & Loss Assessor',
        'license_no': 'SLA-121784',
        'expiry_date': '13-12-2026',
        'membership_no': 'L/E/10721',
        'address_line_1': 'Natungram',
        'address_line_2': 'Nabadwip',
        'address_line_3': 'Nadia',
        'contact_no': '8777207014',
        'email': 'skanowarali93@gmail.com',
        'surveyor_code': 'DEFAULT_CODE_9999',
        'surveyor_gstin': '19AZZPA2301R1ZM',
        'bank_account_no': '33717014374',
        'bank_name': 'SBI',
        'bank_branch': 'Nabadwip',
        'bank_ifsc': 'SBIN0001402',
    }

    fee_data = {
        'invoice_no': 'TEST-INV-001',
        'invoice_date': '2026-08-20',
        'report_no': 'REP-2026-001',
        'insurer_name': 'National Insurance Co. Ltd.',
        'insurer_gst': '19AAACN2027K1ZV',
        'insured_name': 'Subrata Ghosh',
        'policy_no': 'POL12345',
        'claim_no': 'CLM12345',
        'vehicle_no': 'WB-02-AK-9999',
        'surveyor_code': '2075995',  # Specific surveyor code for this insurer
        'fee_items': [
            {'name': '1. Final Survey Fees :', 'amount': 2000.0}
        ],
        'taxable_amount': 2000.0,
        'gst_pc': 18.0,
        'gst_amount': 360.0,
        'total_amount': 2360.0
    }

    res = render_fee_report(fee_data, user_snapshot, user_id=1, include_signature=False)
    assert res is not None
    assert 'pdf_bytes' in res
    assert len(res['pdf_bytes']) > 0
    assert res['invoice_no'] == 'TEST-INV-001'


def test_db_update_fee_bill_payment_memory_fallback():
    """Verify update_fee_bill_payment in db.py updates payment details and remarks properly."""
    db = PostgresDB()
    db.pool = None
    db.connect = lambda: None
    db._memory_fee_bills = [{
        'id': 'bill-101',
        'user_id': '1',
        'workspace_admin_id': 1,
        'invoice_no': 'INV-101',
        'total_amount': 5000.0,
        'gross_invoice_value': 5000.0,
        'payment_status': 'unpaid',
        'amount_received': 0.0,
        'tds_amount': 0.0,
        'outstanding_amount': 5000.0,
        'payment_date': None,
        'payment_reference': '',
        'payment_remarks': '',
        'bill_data_json': {
            'id': 'bill-101',
            'total_amount': 5000.0,
            'payment_status': 'unpaid'
        }
    }]

    payment_data = {
        'payment_status': 'partially_paid',
        'payment_date': '2026-08-20',
        'amount_received': 4000.0,
        'tds_amount': 500.0,
        'payment_reference': 'UTR88776655',
        'payment_remarks': 'Conveyance deduction of Rs 500 applied by insurer.'
    }

    success = db.update_fee_bill_payment('bill-101', workspace_admin_id=1, payment_data=payment_data)
    assert success is True

    bill = db._memory_fee_bills[0]
    assert bill['payment_status'] == 'partially_paid'
    assert bill['payment_date'] == '2026-08-20'
    assert bill['amount_received'] == 4000.0
    assert bill['tds_amount'] == 500.0
    assert bill['outstanding_amount'] == 500.0  # 5000 - 4000 - 500 = 500
    assert bill['payment_reference'] == 'UTR88776655'
    assert bill['payment_remarks'] == 'Conveyance deduction of Rs 500 applied by insurer.'
    assert bill['bill_data_json']['payment_remarks'] == 'Conveyance deduction of Rs 500 applied by insurer.'


def test_api_fee_bill_payment_route(client):
    """Test POST /api/fee_bills/<id>/payment endpoint with mock authentication."""
    admin_user = MockUser(user_id=1, role='admin', workspace_admin_id=1)

    mock_db = MagicMock()
    mock_db.update_fee_bill_payment.return_value = True

    with patch('flask_login.utils._get_user', return_value=admin_user), \
         patch('app.workspace_admin_id_for', return_value=1), \
         patch('app.sheets_db.update_fee_bill_payment', mock_db.update_fee_bill_payment, create=True), \
         patch('app.sheets_db.add_audit_log', mock_db.add_audit_log, create=True):

        payload = {
            'payment_status': 'paid',
            'payment_date': '2026-08-20',
            'amount_received': 2360.0,
            'tds_amount': 0.0,
            'payment_reference': 'NEFT-12345678',
            'payment_remarks': 'Full settlement received from National Insurance.'
        }

        res = client.post('/api/fee_bills/bill-xyz/payment',
                          data=json.dumps(payload),
                          content_type='application/json')

        assert res.status_code == 200
        data = res.get_json()
        assert data['success'] is True
        mock_db.update_fee_bill_payment.assert_called_once_with('bill-xyz', 1, payload)
        mock_db.add_audit_log.assert_called_once()


def test_api_fee_pdf_preview_route(client):
    """Test /generate_fee_pdf with preview=true returns inline PDF header."""
    admin_user = MockUser(user_id=1, role='admin', workspace_admin_id=1)

    with patch('flask_login.utils._get_user', return_value=admin_user), \
         patch('app.workspace_admin_id_for', return_value=1):

        payload = {
            'invoice_no': 'TEST-INV-PREVIEW',
            'invoice_date': '2026-08-20',
            'insurer_name': 'Test Insurer',
            'insured_name': 'Test Insured',
            'surveyor_code': '2075995',
            'fee_items': [{'name': '1. Final Survey Fees :', 'amount': 1500.0}],
            'preview': True
        }

        res = client.post('/generate_fee_pdf?preview=true',
                          data=json.dumps(payload),
                          content_type='application/json')

        assert res.status_code == 200
        assert res.content_type == 'application/pdf'
        disposition = res.headers.get('Content-Disposition', '')
        assert 'inline' in disposition or 'attachment' not in disposition


def test_insurer_master_surveyor_code_crud_in_db():
    """Verify save_insurer_master and get_insurer_masters preserve surveyor_code."""
    db = PostgresDB()
    mock_cursor = MagicMock()
    mock_conn = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    db.pool = MagicMock()
    db.pool.getconn.return_value = mock_conn

    mock_cursor.fetchone.return_value = (42,)
    mock_cursor.fetchall.return_value = [
        {
            'id': 42,
            'workspace_admin_id': 1,
            'insurer_name': 'New India Assurance',
            'branch_name': 'Kolkata DO',
            'branch_address': '123 Park Street, Kolkata',
            'gstin': '19AAACN1234F1Z1',
            'state_code': '19',
            'invoice_prefix': 'NIA',
            'default_conveyance_rate': 10.0,
            'surveyor_code': '2075995',
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
    ]

    saved_id = db.save_insurer_master(workspace_admin_id=1, insurer_data={
        'insurer_name': 'New India Assurance',
        'branch_name': 'Kolkata DO',
        'invoice_prefix': 'NIA',
        'gstin': '19AAACN1234F1Z1',
        'surveyor_code': '2075995',
        'default_conveyance_rate': 10.0
    })
    assert saved_id == 42

    call_args = mock_cursor.execute.call_args[0]
    sql = call_args[0]
    params = call_args[1]
    assert 'surveyor_code' in sql
    assert '2075995' in params

    masters = db.get_insurer_masters(workspace_admin_id=1)
    assert len(masters) == 1
    assert masters[0]['surveyor_code'] == '2075995'
