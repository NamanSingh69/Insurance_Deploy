"""
Local In-Memory / Standalone Database Adapter
Used for automated local browser verification and local development when PostgreSQL is not connected.
"""
import uuid
import json
from datetime import datetime
import bcrypt

class LocalDBAdapter:
    def __init__(self):
        client_admin_hash = bcrypt.hashpw('AnowarAdmin@2026'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        pranay_hash = bcrypt.hashpw('PranayAdmin@2026'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        admin_hash = bcrypt.hashpw('69420'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        emp_hash = bcrypt.hashpw('UH65A#DF'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        self.users = {
            '1': {
                'id': '1',
                'username': 'USER',
                'password_hash': emp_hash,
                'full_name': 'SK ANOWAR ALI (Staff)',
                'qualifications': '(B.Tech (Automobile), LIIISLA)',
                'designation': 'Surveyor Assistant',
                'license_no': 'SLA-121784',
                'expiry_date': '13-12-2026',
                'membership_no': 'L/E/10721',
                'address_line_1': 'Natungram, P.O- Sondanga,',
                'address_line_2': 'P.S Nabadwip, City - Krishnanagar,',
                'address_line_3': 'Dist-Nadia, W.B.-741125',
                'contact_no': '8777370714',
                'email': 'skanowarali93@gmail.com',
                'role': 'employee',
                'admin_id': '3',
                'permissions': {},
                'must_change_password': False,
                'is_locked': False
            },
            '2': {
                'id': '2',
                'username': 'NAMAN',
                'password_hash': admin_hash,
                'full_name': 'Naman Singh',
                'qualifications': 'B.Tech',
                'designation': 'Developer & Administrator',
                'license_no': 'SLA-ADMIN-01',
                'expiry_date': '31-12-2030',
                'membership_no': 'L/E/ADMIN',
                'address_line_1': 'Kolkata, WB',
                'address_line_2': '',
                'address_line_3': '',
                'contact_no': '9999999999',
                'email': 'naman@skinsurance.tech',
                'role': 'admin',
                'admin_id': '2',
                'permissions': {},
                'must_change_password': False,
                'is_locked': False
            },
            '3': {
                'id': '3',
                'username': 'SKANOWAR',
                'password_hash': client_admin_hash,
                'full_name': 'SK ANOWAR ALI',
                'qualifications': '(B.Tech (Automobile), LIIISLA)',
                'designation': 'Surveyor & Loss Assessor',
                'license_no': 'SLA-121784',
                'expiry_date': '13-12-2026',
                'membership_no': 'L/E/10721',
                'address_line_1': 'Natungram, P.O- Sondanga,',
                'address_line_2': 'P.S Nabadwip, City - Krishnanagar,',
                'address_line_3': 'Dist-Nadia, W.B.-741125',
                'contact_no': '8777370714',
                'email': 'skanowarali93@gmail.com',
                'role': 'admin',
                'admin_id': '3',
                'surveyor_code': '2075995',
                'surveyor_gstin': '19AZZPA2301R1ZM',
                'bank_account_no': '33717014374',
                'bank_name': 'State Bank Of India (SBI)',
                'bank_branch': 'Nabadwip (01402)',
                'bank_ifsc': 'SBIN0001402',
                'permissions': {},
                'must_change_password': False,
                'is_locked': False
            },
            '4': {
                'id': '4',
                'username': 'PRANAYMAITY',
                'password_hash': pranay_hash,
                'full_name': 'Pranay Maity',
                'qualifications': '(B.Tech, Surveyor)',
                'designation': 'Surveyor & Loss Assessor',
                'license_no': 'SLA-PRANAY',
                'expiry_date': '31-12-2027',
                'membership_no': 'L/E/PRANAY',
                'address_line_1': 'Kolkata, West Bengal',
                'address_line_2': '',
                'address_line_3': '',
                'contact_no': '9876543210',
                'email': 'pranaymaity@gmail.com',
                'role': 'admin',
                'admin_id': '4',
                'permissions': {},
                'must_change_password': False,
                'is_locked': False
            },
            '5': {
                'id': '5',
                'username': 'USER1',
                'password_hash': emp_hash,
                'full_name': 'USER1 (Assistant)',
                'qualifications': 'Surveyor Staff',
                'designation': 'Field Assistant',
                'license_no': '',
                'expiry_date': '',
                'membership_no': '',
                'address_line_1': '',
                'address_line_2': '',
                'address_line_3': '',
                'contact_no': '',
                'email': 'user1@pranaysurvey.in',
                'role': 'employee',
                'admin_id': '4',
                'permissions': {},
                'must_change_password': False,
                'is_locked': False
            }
        }
        self.reports = {}
        self.fee_bills = {}
        self.assets = {}
        self.jobs = {}
        self.invoice_seq = 1

    def connect(self):
        pass

    def close_scoped_connection(self):
        pass

    def get_user_by_username(self, username):
        if not username:
            return None
        t = str(username).strip().lower()
        if t == 'pranay':
            t = 'pranaymaity'
        for u in self.users.values():
            if u['username'].strip().lower() == t:
                return dict(u)
        return None

    def get_user_by_id(self, user_id):
        u = self.users.get(str(user_id))
        return dict(u) if u else None

    def create_user(self, user_data):
        new_id = str(len(self.users) + 1)
        user_data['id'] = new_id
        self.users[new_id] = user_data
        return new_id

    def get_workspace_dashboard(self, workspace_admin_id, *args, **kwargs):
        ws_reports = [r for r in self.reports.values() if str(r.get('workspace_admin_id')) == str(workspace_admin_id)]
        ws_bills = [b for b in self.fee_bills.values() if str(b.get('workspace_admin_id')) == str(workspace_admin_id)]
        return {
            'total_claims': len(ws_reports),
            'pending_claims': sum(1 for r in ws_reports if r.get('status') != 'closed'),
            'completed_claims': sum(1 for r in ws_reports if r.get('status') == 'closed'),
            'new_appointment': 0, 'inspection_pending': 0, 'documents_awaited': 0,
            'report_under_preparation': 0, 'report_submitted': len(ws_reports), 'closed': 0,
            'total_invoiced': sum(float(b.get('total_amount') or b.get('gross_total') or 0) for b in ws_bills),
            'amount_received': 0,
            'outstanding_fees': sum(float(b.get('total_amount') or b.get('gross_total') or 0) for b in ws_bills),
            'overdue_count': 0
        }

    def get_workspace_reports_page(self, workspace_admin_id, search_term='', page=1, page_size=50, *args, **kwargs):
        user_id = kwargs.get('user_id')
        role = kwargs.get('role')
        items = [r for r in self.reports.values() if str(r.get('workspace_admin_id')) == str(workspace_admin_id)]
        if role == 'employee' and user_id:
            items = [r for r in items if str(r.get('user_id')) == str(user_id) or str(r.get('created_by')) == str(user_id)]
        return {
            'items': items,
            'page': page,
            'page_size': page_size,
            'total': len(items)
        }

    def get_accessible_reports_page(self, workspace_admin_id, user_id, search_term='', page=1, page_size=50, role=None, *args, **kwargs):
        items = [r for r in self.reports.values() if str(r.get('workspace_admin_id')) == str(workspace_admin_id)]
        if role == 'employee' and user_id:
            items = [r for r in items if str(r.get('user_id')) == str(user_id) or str(r.get('created_by')) == str(user_id)]
        return {
            'items': items,
            'page': page,
            'page_size': page_size,
            'total': len(items)
        }

    def get_user_reports_page(self, *args, **kwargs):
        items = list(self.reports.values())
        return {
            'items': items,
            'page': 1,
            'page_size': 50,
            'total': len(items)
        }

    def get_workspace_report_by_id(self, report_id, workspace_admin_id=None):
        r = self.reports.get(str(report_id))
        if r and workspace_admin_id and str(r.get('workspace_admin_id')) != str(workspace_admin_id):
            return None
        return r

    def reserve_report_number(self, workspace_admin_id, prefix, year):
        self.invoice_seq += 1
        return self.invoice_seq

    def save_workspace_report(self, user_id, workspace_admin_id, report_data=None, status=None, survey_type=None):
        if report_data is None and isinstance(workspace_admin_id, dict):
            report_data = workspace_admin_id
            workspace_admin_id = user_id
        rep_id = str((report_data or {}).get('id') or uuid.uuid4())
        survey_rep = (report_data or {}).get('survey_report') or {}
        item = {
            'id': rep_id,
            'report_id': rep_id,
            'user_id': str(user_id),
            'workspace_admin_id': str(workspace_admin_id or user_id),
            'report_no': survey_rep.get('report_no', f'SR/2026/{self.invoice_seq:02d}'),
            'claim_no': survey_rep.get('claim_no', ''),
            'insured_name': survey_rep.get('insured', ''),
            'insured': survey_rep.get('insured', ''),
            'vehicle_no': survey_rep.get('vehicle_regn_no', ''),
            'vehicle_regn_no': survey_rep.get('vehicle_regn_no', ''),
            'policy_no': survey_rep.get('policy_no', ''),
            'insurer': survey_rep.get('insurer', ''),
            'date_of_loss': survey_rep.get('date_of_loss', ''),
            'status': status or (report_data or {}).get('claim_meta', {}).get('status', 'report_submitted'),
            'survey_type': survey_type or (report_data or {}).get('claim_meta', {}).get('survey_type', 'final'),
            'report_data': report_data or {},
            'created_at': datetime.now().isoformat()
        }
        self.reports[rep_id] = item
        return rep_id

    def save_fee_bill(self, user_id, data, workspace_admin_id=None):
        bill_id = str(data.get('id') or uuid.uuid4())
        data['id'] = bill_id
        data['user_id'] = str(user_id)
        data['workspace_admin_id'] = str(workspace_admin_id or user_id)
        data['created_at'] = datetime.now().isoformat()
        self.fee_bills[bill_id] = data
        return bill_id

    def get_workspace_fee_bills(self, workspace_admin_id, month=None, insurer=None, report_id=None, user_id=None, role=None):
        bills = [b for b in self.fee_bills.values() if str(b.get('workspace_admin_id')) == str(workspace_admin_id)]
        if role == 'employee' and user_id:
            bills = [b for b in bills if str(b.get('user_id')) == str(user_id)]
        if month:
            bills = [b for b in bills if str(b.get('invoice_date', '')).startswith(month)]
        if insurer:
            bills = [b for b in bills if insurer.lower() in str(b.get('insurer_name', '')).lower()]
        if report_id:
            bills = [b for b in bills if str(b.get('report_id')) == str(report_id)]
        return bills

    def get_fee_bill_by_id(self, bill_id, workspace_admin_id=None):
        return self.fee_bills.get(str(bill_id))

    def delete_fee_bill(self, bill_id, user_id, workspace_admin_id=None):
        if str(bill_id) in self.fee_bills:
            del self.fee_bills[str(bill_id)]
            return True
        return False

    def get_next_insurer_invoice_number(self, workspace_admin_id, prefix='NIC'):
        self.invoice_seq += 1
        return f"{prefix}/2026/{self.invoice_seq:04d}"

    def get_gmail_integration(self, workspace_admin_id):
        return None

    def get_drive_integration(self, workspace_admin_id):
        return None

    def get_pending_gmail_messages(self, workspace_admin_id=None, *args, **kwargs):
        return []

    def get_gmail_sender_domains(self, workspace_admin_id=None, *args, **kwargs):
        return []

    def create_asset(self, user_id, storage_kind='private_local', storage_locator=None, *args, **kwargs):
        asset_id = str(uuid.uuid4())
        asset = {
            'id': asset_id,
            'user_id': str(user_id),
            'storage_kind': storage_kind,
            'storage_locator': storage_locator,
            'original_name': kwargs.get('filename', 'asset.bin'),
            'mime_type': kwargs.get('mime_type', 'application/octet-stream'),
            'purpose': kwargs.get('purpose', 'photo'),
            'size_bytes': kwargs.get('size_bytes', 0),
            'checksum_sha256': kwargs.get('checksum_sha256', '')
        }
        self.assets[asset_id] = asset
        return asset

    def get_asset_for_access(self, asset_id, user_id=None, workspace_admin_id=None):
        return self.assets.get(str(asset_id))

    def create_job(self, user_id, kind, payload=None):
        job_id = str(uuid.uuid4())
        job = {
            'id': job_id,
            'user_id': str(user_id),
            'kind': kind,
            'status': 'completed',
            'payload': payload,
            'created_at': datetime.now().isoformat()
        }
        self.jobs[job_id] = job
        return job

    def get_job_for_user(self, job_id, user_id=None):
        return self.jobs.get(str(job_id))

    def upload_report_pdf(self, pdf_bytes, filename_pdf, vehicle_no):
        return "https://drive.google.com/mock_report.pdf"

    def delete_accessible_report(self, report_id, workspace_admin_id=None, user_id=None):
        if str(report_id) in self.reports:
            del self.reports[str(report_id)]
            return True
        return False

    def delete_report(self, report_id, user_id=None):
        if str(report_id) in self.reports:
            del self.reports[str(report_id)]
            return True
        return False

