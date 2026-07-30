import base64
import io
import json
from datetime import datetime
from unittest.mock import MagicMock, patch

from openpyxl import load_workbook

import app as app_module


def _employee(mock_user, **overrides):
    user = dict(mock_user)
    user.update({
        'id': '2',
        'role': 'employee',
        'admin_id': 1,
        'permissions': {},
        'is_locked': False,
        'must_change_password': False,
    })
    user.update(overrides)
    return user


def _authenticate_as(client, mock_sheets_db, user):
    mock_sheets_db.get_user_by_id.return_value = user
    with client.session_transaction() as session:
        session['_user_id'] = str(user['id'])
        session['_fresh'] = True


def _gmail_message(sender='claims@insurer.example', subject='Motor claim intimation'):
    encoded_body = base64.urlsafe_b64encode(b'Claim appointment details').decode('ascii')
    return {
        'payload': {
            'mimeType': 'multipart/alternative',
            'headers': [
                {'name': 'From', 'value': f'Claims Desk <{sender}>'},
                {'name': 'Subject', 'value': subject},
                {'name': 'Date', 'value': 'Wed, 29 Jul 2026 10:00:00 +0000'},
            ],
            'parts': [{'mimeType': 'text/plain', 'body': {'data': encoded_body}}],
        }
    }


def _gmail_service(message_ids, messages):
    gmail = MagicMock()
    messages_api = gmail.users.return_value.messages.return_value
    messages_api.list.return_value.execute.return_value = {'messages': [{'id': message_id} for message_id in message_ids]}

    def get_message(**kwargs):
        request = MagicMock()
        request.execute.return_value = messages[kwargs['id']]
        return request

    messages_api.get.side_effect = get_message
    return gmail, messages_api


def _gemini_models(parsed):
    primary = MagicMock()
    primary.generate_content.return_value.text = json.dumps(parsed)
    return primary, MagicMock()


def test_employee_cannot_access_financial_or_user_management_routes(client, mock_sheets_db, mock_user):
    employee = _employee(mock_user)
    _authenticate_as(client, mock_sheets_db, employee)

    requests = [
        ('get', '/api/fee_bills'),
        ('get', '/api/fees_summary'),
        ('get', '/download_fees_excel?month=2026-07'),
        ('get', '/download_consolidated_csv?from_date=2026-07-01&to_date=2026-07-31'),
        ('get', '/api/next_invoice_no'),
        ('post', '/generate_fee_pdf'),
        ('get', '/api/admin/users'),
    ]
    for method, path in requests:
        response = getattr(client, method)(path, json={} if method == 'post' else None)
        assert response.status_code == 403

    gmail_response = client.post('/api/gmail/sync', json={})
    assert gmail_response.status_code == 403


def test_employee_load_redacts_fees_and_save_preserves_stored_values(client, mock_sheets_db, mock_user):
    employee = _employee(mock_user)
    _authenticate_as(client, mock_sheets_db, employee)
    stored_data = {
        'survey_report': {'report_no': 'REP/2026/01', 'claim_no': 'CLM-1'},
        'assessment': {
            'page3_details': {
                'fee_items': [{'name': 'Professional fee', 'amount': '1500'}],
                'photo_charges': 100,
                'fees_subtotal': 1500,
                'total_before_gst': 1600,
                'cgst': 144,
                'sgst': 144,
                'grand_total': 1888,
            }
        },
        'fee_breakdown': {'professional_fee': 1500, 'outstanding_amount': 900},
    }
    mock_sheets_db.get_accessible_report_by_id.return_value = {
        'id': 'report-1', 'workspace_admin_id': 1, 'status': 'inspection_pending',
        'survey_type': 'final', 'report_data_json': json.dumps(stored_data),
    }

    loaded = client.get('/load_report/report-1')
    assert loaded.status_code == 200
    loaded_data = loaded.get_json()
    assert 'fee_breakdown' not in loaded_data
    assert 'fee_items' not in loaded_data['assessment']['page3_details']
    assert 'grand_total' not in loaded_data['assessment']['page3_details']

    edited = {
        'survey_report': {'report_no': 'REP/2026/01', 'claim_no': 'CLM-1'},
        'assessment': {'page3_details': {'fee_items': [{'name': 'Attempted overwrite', 'amount': '1'}]}},
        'fee_breakdown': {'professional_fee': 1},
        '_current_report_id': 'report-1',
    }
    saved = client.post('/save_report', json=edited)
    assert saved.status_code == 200
    committed_payload = mock_sheets_db.save_workspace_report.call_args.args[2]
    assert committed_payload['fee_breakdown'] == stored_data['fee_breakdown']
    assert committed_payload['assessment']['page3_details']['fee_items'] == stored_data['assessment']['page3_details']['fee_items']
    assert committed_payload['assessment']['page3_details']['grand_total'] == 1888


def test_locked_account_is_denied_on_an_existing_session(client, mock_sheets_db, mock_user):
    _authenticate_as(client, mock_sheets_db, _employee(mock_user, is_locked=True))

    response = client.get('/api/dashboard')
    assert response.status_code == 403
    assert response.get_json()['error'] == 'This account is locked.'


def test_workspace_dashboard_hides_financial_values_from_employee(client, mock_sheets_db, mock_user):
    mock_sheets_db.get_workspace_dashboard.return_value = {
        'total_claims': 3, 'pending_claims': 2, 'completed_claims': 1,
        'new_appointment': 1, 'inspection_pending': 1, 'documents_awaited': 0,
        'report_under_preparation': 0, 'report_submitted': 1, 'closed': 0,
        'total_invoiced': 5000, 'amount_received': 1000, 'outstanding_fees': 4000, 'overdue_count': 1,
    }
    _authenticate_as(client, mock_sheets_db, _employee(mock_user))

    employee_response = client.get('/api/dashboard')
    assert employee_response.status_code == 200
    assert 'total_invoiced' not in employee_response.get_json()


def test_workspace_dashboard_exposes_financial_values_to_admin(authenticated_client, mock_sheets_db):
    mock_sheets_db.get_workspace_dashboard.return_value = {
        'total_claims': 3, 'pending_claims': 2, 'completed_claims': 1,
        'new_appointment': 1, 'inspection_pending': 1, 'documents_awaited': 0,
        'report_under_preparation': 0, 'report_submitted': 1, 'closed': 0,
        'total_invoiced': 5000, 'amount_received': 1000, 'outstanding_fees': 4000, 'overdue_count': 1,
    }
    admin_response = authenticated_client.get('/api/dashboard')
    assert admin_response.status_code == 200
    assert admin_response.get_json()['total_invoiced'] == 5000


def test_claim_register_filters_and_creates_shared_workspace_claim(client, mock_sheets_db, mock_user):
    _authenticate_as(client, mock_sheets_db, _employee(mock_user))
    mock_sheets_db.get_workspace_reports_page.return_value = {
        'items': [{'id': 'r1', 'claim_no': 'CLM-1'}], 'page': 1, 'page_size': 25, 'total': 1,
    }

    listing = client.get('/api/claims?q=CLM&status=inspection_pending&month=2026-07&insurer=Example&page=1&page_size=25')
    assert listing.status_code == 200
    mock_sheets_db.get_workspace_reports_page.assert_called_once_with(
        1, 'CLM', 1, 25, status='inspection_pending', month='2026-07', insurer='Example')

    creation = client.post('/api/claims', json={
        'claim_no': 'CLM-2', 'vehicle_no': 'WB-01-AB-1234', 'insured_name': 'Insured',
        'policy_no': 'POL-2', 'insurer': 'Example Insurance', 'survey_type': 'spot',
        'status': 'new_appointment',
    })
    assert creation.status_code == 201
    saved_payload = mock_sheets_db.save_workspace_report.call_args.args[2]
    assert saved_payload['claim_meta']['survey_type'] == 'spot'
    assert saved_payload['assessment']['report_type'] == 'Spot Report'


def test_legacy_report_edits_stay_with_the_original_owner(client, mock_sheets_db, mock_user):
    _authenticate_as(client, mock_sheets_db, mock_user)
    mock_sheets_db.get_accessible_report_by_id.return_value = {
        'id': 'legacy-1', 'workspace_admin_id': None,
        'report_data_json': json.dumps({'survey_report': {'report_no': 'LEG/01'}}),
    }

    response = client.post('/save_report', json={
        'survey_report': {'report_no': 'LEG/01'}, 'assessment': {}, '_current_report_id': 'legacy-1',
    })
    assert response.status_code == 200
    mock_sheets_db.save_report.assert_called_once()
    mock_sheets_db.save_workspace_report.assert_not_called()


def test_gmail_sync_creates_a_spot_draft_with_the_callers_model_resolver(client, mock_sheets_db, mock_user):
    _authenticate_as(client, mock_sheets_db, mock_user)
    mock_sheets_db.get_gmail_sender_domains.return_value = [{'id': 1, 'domain': 'insurer.example'}]
    gmail, messages_api = _gmail_service(['message-1'], {'message-1': _gmail_message(subject='Preliminary spot survey appointment')})
    parsed = {
        'claim_no': 'CLM-10', 'vehicle_no': 'WB-10-AA-0001', 'insured_name': 'Test Insured',
        'policy_no': 'POL-10', 'insurer': 'Example Insurer', 'date_of_loss': '2026-07-28',
    }
    models = _gemini_models(parsed)
    mock_sheets_db.reserve_report_number.return_value = 7
    mock_sheets_db.save_workspace_report.return_value = 'report-10'

    with patch.object(app_module, '_gmail_service_for_workspace', return_value=gmail), \
         patch.object(app_module, 'get_generative_models', return_value=models) as resolver:
        response = client.post('/api/gmail/sync', json={})

    assert response.status_code == 200
    assert response.get_json() == {'created': 1, 'merged': 0, 'skipped': 0, 'failed': 0}
    assert messages_api.list.call_args.kwargs['q'] == 'is:unread newer_than:30d'
    resolver.assert_called_once()
    saved_kwargs = mock_sheets_db.save_workspace_report.call_args.kwargs
    saved_payload = mock_sheets_db.save_workspace_report.call_args.args[2]
    assert saved_kwargs['status'] == 'documents_awaited'
    assert saved_kwargs['survey_type'] == 'spot'
    assert saved_payload['survey_report']['claim_no'] == 'CLM-10'
    assert saved_payload['assessment']['report_type'] == 'Spot Report'


def test_gmail_sync_merges_only_missing_metadata_for_same_claim(client, mock_sheets_db, mock_user):
    _authenticate_as(client, mock_sheets_db, mock_user)
    mock_sheets_db.get_gmail_sender_domains.return_value = [{'id': 1, 'domain': 'insurer.example'}]
    gmail, _ = _gmail_service(['message-2'], {'message-2': _gmail_message()})
    mock_sheets_db.find_workspace_report_by_claim_no.return_value = {
        'id': 'existing-report', 'status': 'inspection_pending', 'survey_type': 'final',
        'report_data_json': {
            'survey_report': {'claim_no': 'CLM-10', 'policy_no': 'KEEP-ME', 'insurer': ''},
        },
    }
    models = _gemini_models({
        'claim_no': 'CLM-10', 'vehicle_no': 'WB-10-AA-0001', 'insured_name': 'New Insured',
        'policy_no': 'REPLACE-ME-NOT', 'insurer': 'Example Insurer', 'date_of_loss': '2026-07-28',
    })

    with patch.object(app_module, '_gmail_service_for_workspace', return_value=gmail), \
         patch.object(app_module, 'get_generative_models', return_value=models):
        response = client.post('/api/gmail/sync', json={})

    assert response.status_code == 200
    assert response.get_json()['merged'] == 1
    mock_sheets_db.reserve_report_number.assert_not_called()
    saved_payload = mock_sheets_db.save_workspace_report.call_args.args[2]
    survey = saved_payload['survey_report']
    assert survey['policy_no'] == 'KEEP-ME'
    assert survey['vehicle_regn_no'] == 'WB-10-AA-0001'
    assert survey['insurer'] == 'Example Insurer'


def test_gmail_sync_deduplicates_and_rejects_unapproved_domains(client, mock_sheets_db, mock_user):
    _authenticate_as(client, mock_sheets_db, mock_user)
    mock_sheets_db.get_gmail_sender_domains.return_value = [{'id': 1, 'domain': 'insurer.example'}]
    invalid = client.post('/api/gmail/sync', json={'sender_domain': 'not-approved.example'})
    assert invalid.status_code == 400

    gmail, messages_api = _gmail_service(['already-seen'], {'already-seen': _gmail_message()})
    mock_sheets_db.get_gmail_sync_message.return_value = {'gmail_message_id': 'already-seen'}
    with patch.object(app_module, '_gmail_service_for_workspace', return_value=gmail):
        response = client.post('/api/gmail/sync', json={})

    assert response.status_code == 200
    assert response.get_json()['skipped'] == 1
    messages_api.get.assert_not_called()


def test_gmail_sync_records_parse_failures_and_skips_non_allowlisted_senders(client, mock_sheets_db, mock_user):
    _authenticate_as(client, mock_sheets_db, mock_user)
    mock_sheets_db.get_gmail_sender_domains.return_value = [{'id': 1, 'domain': 'insurer.example'}]

    outsider_gmail, _ = _gmail_service(['outsider'], {'outsider': _gmail_message(sender='mail@other.example')})
    with patch.object(app_module, '_gmail_service_for_workspace', return_value=outsider_gmail), \
         patch.object(app_module, '_parse_claim_intimation_with_gemini') as parser:
        outsider_response = client.post('/api/gmail/sync', json={})
    assert outsider_response.status_code == 200
    assert outsider_response.get_json()['skipped'] == 1
    parser.assert_not_called()

    failing_gmail, _ = _gmail_service(['bad-parse'], {'bad-parse': _gmail_message()})
    with patch.object(app_module, '_gmail_service_for_workspace', return_value=failing_gmail), \
         patch.object(app_module, '_parse_claim_intimation_with_gemini', side_effect=ValueError('invalid model response')):
        failed_response = client.post('/api/gmail/sync', json={})
    assert failed_response.status_code == 200
    assert failed_response.get_json()['failed'] == 1
    assert mock_sheets_db.record_gmail_sync_message.call_args.kwargs['sync_status'] == 'failed'


def test_claim_parser_uses_the_current_users_selected_or_automatic_resolver(mock_user):
    user = app_module.User({**mock_user, 'gemini_model': ''})
    models = _gemini_models({
        'claim_no': 'CLM-1', 'vehicle_no': '', 'insured_name': '', 'policy_no': '', 'insurer': '', 'date_of_loss': '',
    })
    with patch.object(app_module, 'get_generative_models', return_value=models) as resolver:
        parsed = app_module._parse_claim_intimation_with_gemini('Claim CLM-1', 'Appointment', user)
    resolver.assert_called_once_with(user)
    assert parsed['claim_no'] == 'CLM-1'


def test_admin_fee_excel_is_a_real_workbook(client, mock_sheets_db, mock_user):
    _authenticate_as(client, mock_sheets_db, mock_user)
    mock_sheets_db.get_workspace_fee_bills.return_value = [{
        'invoice_date': '2026-07-29', 'invoice_no': 'EX/01', 'insurer_name': 'Example Insurer',
        'insured_name': 'Insured', 'claim_no': 'CLM-1', 'policy_no': 'POL-1', 'vehicle_no': 'WB-01',
        'professional_fee': 1000, 'gst_pc': 18, 'gst_amount': 180, 'gross_invoice_value': 1180,
        'tds_amount': 100, 'amount_received': 500, 'outstanding_amount': 580,
        'due_date': '2026-08-15', 'payment_status': 'partially_paid', 'invoice_status': 'issued',
    }]

    response = client.get('/download_fees_excel?month=2026-07')
    assert response.status_code == 200
    workbook = load_workbook(io.BytesIO(response.data))
    sheet = workbook['Survey Fee Register']
    assert sheet['B2'].value == 'EX/01'
    assert sheet['N2'].value == 580


def test_motor_survey_migration_declares_workspace_and_gmail_schema():
    with open('migrations/0004_motor_survey_management.sql', encoding='utf-8') as migration_file:
        migration = migration_file.read()
    for fragment in (
        'workspace_admin_id', 'must_change_password', 'gmail_integrations',
        'gmail_sync_messages', 'gmail_sender_domains', 'fee_bills_one_report_idx',
    ):
        assert fragment in migration


def test_employee_can_download_shared_workspace_report_pdf(client, mock_sheets_db, mock_user):
    employee = _employee(mock_user)
    _authenticate_as(client, mock_sheets_db, employee)

    report_data = {
        'survey_report': {'report_no': 'REP/2026/99', 'vehicle_regn_no': 'WB-51-C-4222'},
        'assessment': {'parts': []},
        'fee_breakdown': {'professional_fee': 2000, 'outstanding_amount': 500},
    }
    mock_sheets_db.get_accessible_report_by_id.return_value = {
        'id': 'shared-report-99', 'workspace_admin_id': 1, 'user_id': 1,
        'status': 'report_submitted', 'survey_type': 'final',
        'report_data_json': json.dumps(report_data),
    }

    with patch('modules.pdf.render_report', return_value={'pdf_bytes': b'%PDF-1.4 test pdf content'}) as mock_render:
        response = client.get('/download/report_pdf/shared-report-99')
        assert response.status_code == 200
        assert response.content_type == 'application/pdf'
        assert b'%PDF-1.4' in response.data
        mock_render.assert_called_once()
        # Verify fee fields were redacted for employee rendering
        rendered_dict = mock_render.call_args.args[0]
        assert 'fee_breakdown' not in rendered_dict


def test_employee_cannot_download_unshared_legacy_report_of_another_user(client, mock_sheets_db, mock_user):
    employee = _employee(mock_user)
    _authenticate_as(client, mock_sheets_db, employee)

    # Legacy report owned by user 999 (not matching workspace_admin_id or employee)
    mock_sheets_db.get_accessible_report_by_id.return_value = None

    response = client.get('/download/report_pdf/unshared-legacy-999')
    assert response.status_code == 404

