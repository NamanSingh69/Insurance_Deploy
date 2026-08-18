"""
Tests for API endpoints - report CRUD, photo upload, PDF generation.
"""
import json
import pytest
import sys
import os
import io
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
class TestSaveReportEndpoint:
    """Tests for /save_report endpoint."""
    
    def test_save_report_success(self, authenticated_client, mock_sheets_db, sample_report_data):
        """Test successful report save."""
        mock_sheets_db.save_report.return_value = "new-report-id"
        
        response = authenticated_client.post('/save_report',
                                             json=sample_report_data,
                                             content_type='application/json')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data.get('success') == True or 'id' in data
    
    def test_save_report_missing_report_no(self, authenticated_client, sample_report_data):
        """Test save report without report number."""
        del sample_report_data['survey_report']['report_no']
        
        response = authenticated_client.post('/save_report',
                                             json=sample_report_data,
                                             content_type='application/json')
        
        # Should fail or handle gracefully
        assert response.status_code in [200, 400]
    
    def test_save_report_empty_data(self, authenticated_client):
        """Test save report with empty data."""
        response = authenticated_client.post('/save_report',
                                             json={},
                                             content_type='application/json')
        
        assert response.status_code in [200, 400]


class TestGetSavedReportsEndpoint:
    """Tests for /get_saved_reports endpoint."""
    
    def test_get_reports_empty(self, authenticated_client, mock_sheets_db):
        """Test getting reports when none exist."""
        mock_sheets_db.get_accessible_reports_page.return_value = {
            'items': [],
            'page': 1,
            'page_size': 50,
            'total': 0
        }
        
        response = authenticated_client.get('/get_saved_reports')
        
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, dict)
        assert len(data.get('items', [])) == 0
        assert data.get('total') == 0
    
    def test_get_reports_with_data(self, authenticated_client, mock_sheets_db):
        """Test getting reports with existing data."""
        mock_reports = [
            {
                'id': '1',
                'report_no': 'SR-001',
                'insured_name': 'Test Insured',
                'vehicle_no': 'WB-01-AB-1234',
                'saved_at': '2026-01-29T12:00:00'
            }
        ]
        mock_sheets_db.get_accessible_reports_page.return_value = {
            'items': mock_reports,
            'page': 1,
            'page_size': 50,
            'total': 1
        }
        
        response = authenticated_client.get('/get_saved_reports')
        
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, dict)
        items = data.get('items', [])
        assert len(items) == 1
        assert items[0]['report_no'] == 'SR-001'
    
    def test_get_reports_with_search(self, authenticated_client, mock_sheets_db):
        """Test searching reports."""
        mock_sheets_db.get_accessible_reports_page.return_value = {
            'items': [{'id': '1', 'report_no': 'SR-001', 'insured_name': 'john'}],
            'page': 1,
            'page_size': 50,
            'total': 1
        }
        
        response = authenticated_client.get('/get_saved_reports?query=john')
        
        assert response.status_code == 200


class TestLoadReportEndpoint:
    """Tests for /load_report/<report_id> endpoint."""
    
    def test_load_report_success(self, authenticated_client, mock_sheets_db, sample_report_data):
        """Test loading existing report."""
        mock_sheets_db.get_report_by_id.return_value = {
            'id': 'test-id',
            'user_id': '1',
            'report_no': 'SR-001',
            'report_data_json': '{"survey_report": {}, "assessment": {}}'
        }
        
        response = authenticated_client.get('/load_report/test-id')
        
        assert response.status_code in [200, 404]
    
    def test_load_report_not_found(self, authenticated_client, mock_sheets_db):
        """Test loading non-existent report."""
        mock_sheets_db.get_report_by_id.return_value = None
class TestSaveReportEndpoint:
    """Tests for /save_report endpoint."""
    
    def test_save_report_success(self, authenticated_client, mock_sheets_db, sample_report_data):
        """Test successful report save."""
        mock_sheets_db.save_report.return_value = "new-report-id"
        
        response = authenticated_client.post('/save_report',
                                             json=sample_report_data,
                                             content_type='application/json')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data.get('success') == True or 'id' in data
    
    def test_save_report_missing_report_no(self, authenticated_client, sample_report_data):
        """Test save report without report number."""
        del sample_report_data['survey_report']['report_no']
        
        response = authenticated_client.post('/save_report',
                                             json=sample_report_data,
                                             content_type='application/json')
        
        # Should fail or handle gracefully
        assert response.status_code in [200, 400]
    
    def test_save_report_empty_data(self, authenticated_client):
        """Test save report with empty data."""
        response = authenticated_client.post('/save_report',
                                             json={},
                                             content_type='application/json')
        
        assert response.status_code in [200, 400]


class TestGetSavedReportsEndpoint:
    """Tests for /get_saved_reports endpoint."""
    
    def test_get_reports_empty(self, authenticated_client, mock_sheets_db):
        """Test getting reports when none exist."""
        mock_sheets_db.get_accessible_reports_page.return_value = {
            'items': [],
            'page': 1,
            'page_size': 50,
            'total': 0
        }
        
        response = authenticated_client.get('/get_saved_reports')
        
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, dict)
        assert len(data.get('items', [])) == 0
        assert data.get('total') == 0
    
    def test_get_reports_with_data(self, authenticated_client, mock_sheets_db):
        """Test getting reports with existing data."""
        mock_reports = [
            {
                'id': '1',
                'report_no': 'SR-001',
                'insured_name': 'Test Insured',
                'vehicle_no': 'WB-01-AB-1234',
                'saved_at': '2026-01-29T12:00:00'
            }
        ]
        mock_sheets_db.get_accessible_reports_page.return_value = {
            'items': mock_reports,
            'page': 1,
            'page_size': 50,
            'total': 1
        }
        
        response = authenticated_client.get('/get_saved_reports')
        
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, dict)
        items = data.get('items', [])
        assert len(items) == 1
        assert items[0]['report_no'] == 'SR-001'
    
    def test_get_reports_with_search(self, authenticated_client, mock_sheets_db):
        """Test searching reports."""
        mock_sheets_db.get_accessible_reports_page.return_value = {
            'items': [{'id': '1', 'report_no': 'SR-001', 'insured_name': 'john'}],
            'page': 1,
            'page_size': 50,
            'total': 1
        }
        
        response = authenticated_client.get('/get_saved_reports?query=john')
        
        assert response.status_code == 200


class TestLoadReportEndpoint:
    """Tests for /load_report/<report_id> endpoint."""
    
    def test_load_report_success(self, authenticated_client, mock_sheets_db, sample_report_data):
        """Test loading existing report."""
        mock_sheets_db.get_report_by_id.return_value = {
            'id': 'test-id',
            'user_id': '1',
            'report_no': 'SR-001',
            'report_data_json': '{"survey_report": {}, "assessment": {}}'
        }
        
        response = authenticated_client.get('/load_report/test-id')
        
        assert response.status_code in [200, 404]
    
    def test_load_report_not_found(self, authenticated_client, mock_sheets_db):
        """Test loading non-existent report."""
        mock_sheets_db.get_report_by_id.return_value = None
        
        response = authenticated_client.get('/load_report/nonexistent-id')
        
        assert response.status_code in [404, 500]


class TestDeleteReportEndpoint:
    """Tests for /delete_report/<report_id> endpoint."""
    
    def test_delete_report_success(self, authenticated_client, mock_sheets_db):
        # Mock successful deletion (True)
        mock_sheets_db.delete_report.return_value = True
        
        with patch('app.bcrypt.check_password_hash', return_value=True):
            # Must provide password in JSON body
            response = authenticated_client.delete('/delete_report/test-id', json={'password': 'any_password'})
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['message'] == 'Report deleted successfully'
    
    def test_delete_report_not_found(self, authenticated_client, mock_sheets_db):
        # Mock deletion failing (False)
        mock_sheets_db.delete_accessible_report.return_value = False
        
        with patch('app.bcrypt.check_password_hash', return_value=True):
            response = authenticated_client.delete('/delete_report/nonexistent-id', json={'password': 'any_password'})
            assert response.status_code in [404]

    def test_delete_report_forbidden_for_employee(self, app, mock_sheets_db):
        """Verify employee role is rejected when attempting to delete a report."""
        employee_user = {
            'id': '10', 'username': 'emp1', 'role': 'employee', 'admin_id': 2,
            'password_hash': '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.HJtF/OqJkKxhTu',
            'permissions': {}, 'is_locked': False, 'must_change_password': False
        }
        mock_sheets_db.get_user_by_id.return_value = employee_user
        mock_sheets_db.get_user_by_username.return_value = employee_user

        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['_user_id'] = '10'
                sess['_fresh'] = True
            with patch('app.bcrypt.check_password_hash', return_value=True):
                response = client.delete('/delete_report/test-id', json={'password': 'any_password'})
                assert response.status_code == 403
                data = response.get_json()
                assert 'Administrator access is required' in data.get('error', '')



class TestUploadPhotoEndpoint:
    """Tests for /upload_photo endpoint."""
    
    def test_upload_photo_success(self, authenticated_client, mock_sheets_db):
        """Test successful photo upload returns private asset route."""
        valid_png = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x03\x01\x01\x00\xc9\xfe\x92\xef\x00\x00\x00\x00IEND\xaeB`\x82'
        data = {
            'photo': (io.BytesIO(valid_png), 'test.png')
        }
        
        response = authenticated_client.post('/upload_photo',
                                             data=data,
                                             content_type='multipart/form-data')
        
        assert response.status_code == 200
        result = response.get_json()
        assert result.get('success') is True
        assert '/assets/' in result.get('url', '')
    
    def test_upload_photo_no_file(self, authenticated_client):
        """Test upload without file."""
        response = authenticated_client.post('/upload_photo',
                                             data={},
                                             content_type='multipart/form-data')
        
        assert response.status_code == 400
        result = response.get_json()
        assert 'error' in result
    
    def test_upload_photo_empty_filename(self, authenticated_client):
        """Test upload with empty filename."""
        data = {
            'photo': (io.BytesIO(b''), '')
        }
        
        response = authenticated_client.post('/upload_photo',
                                             data=data,
                                             content_type='multipart/form-data')
        
        assert response.status_code == 400


class TestGenerateFilesEndpoint:
    """Tests for /generate_files endpoint."""
    
    def test_generate_files_success(self, authenticated_client, sample_report_data):
        """Test successful file generation returns task_id (async pattern)."""
        response = authenticated_client.post('/generate_files',
                                             json=sample_report_data,
                                             content_type='application/json')
        
        assert response.status_code == 202
        data = response.get_json()
        assert 'task_id' in data
    
    def test_generate_files_no_data(self, authenticated_client):
        """Test generate files without data."""
        response = authenticated_client.post('/generate_files',
                                             json={},
                                             content_type='application/json')
        
        assert response.status_code in [400, 500]

    def test_generate_files_end_to_end_worker_execution(self, authenticated_client, sample_report_data, mock_sheets_db):
        """Test queuing generate_files and executing worker completes without binary data error."""
        response = authenticated_client.post('/generate_files',
                                             json=sample_report_data,
                                             content_type='application/json')
        assert response.status_code == 202
        task_id = response.get_json()['task_id']
        
        from worker import run_job
        job = {
            'id': task_id,
            'user_id': 1,
            'kind': 'generate_files',
            'input_json': json.dumps({'report_data': sample_report_data}),
            'attempts': 1,
            'status': 'queued'
        }
        
        user_data = {
            'id': 1, 'username': 'NAMAN', 'full_name': 'Naman Singh',
            'qualifications': 'B.Tech', 'designation': 'Surveyor',
            'license_no': 'SL123', 'expiry_date': '2030-01-01',
            'membership_no': 'M123', 'address_line_1': 'Addr1',
            'address_line_2': 'Addr2', 'address_line_3': 'Addr3',
            'contact_no': '9999999999', 'email': 'test@example.com'
        }
        mock_sheets_db.get_user_by_id.return_value = user_data
        
        # Execute the worker job directly
        run_job(job)
        
        # Verify job completed successfully and created asset
        assert mock_sheets_db.complete_job.called
        completed_args = mock_sheets_db.complete_job.call_args[0]
        completed_result = completed_args[1]
        assert 'asset_id' in completed_result
        assert 'request_id' in completed_result



class TestProcessPDFEndpoint:
    """Tests for /process_pdf endpoint."""
    
    def test_process_pdf_no_file(self, authenticated_client):
        """Test process PDF without file."""
        response = authenticated_client.post('/process_pdf',
                                             data={},
                                             content_type='multipart/form-data')
        
        assert response.status_code == 400
    
    def test_process_pdf_with_mock_file(self, authenticated_client):
        """Test process PDF with mock file returns task_id (async pattern)."""
        pdf_content = b'%PDF-1.4 fake pdf content'
        data = {
            'pdf_file': (io.BytesIO(pdf_content), 'test.pdf', 'application/pdf')
        }
        
        response = authenticated_client.post('/process_pdf',
                                             data=data,
                                             content_type='multipart/form-data')
        
        assert response.status_code == 202
        result = response.get_json()
        assert 'task_id' in result

    def test_process_pdf_status_not_found(self, authenticated_client, mock_sheets_db):
        """Test polling for a non-existent task."""
        mock_sheets_db.get_job_for_user.return_value = None
        response = authenticated_client.get('/process_pdf/status/nonexistent-task-id')
        assert response.status_code == 404


class TestProcessInvoiceEndpoint:
    """Tests for /process_invoice endpoint."""
    
    def test_process_invoice_no_file(self, authenticated_client):
        """Test process invoice without file returns 400."""
        response = authenticated_client.post('/process_invoice',
                                             data={},
                                             content_type='multipart/form-data')
        assert response.status_code == 400
        result = response.get_json()
        assert 'error' in result

    def test_process_invoice_with_mock_file(self, authenticated_client):
        """Test process invoice with mock PDF file returns 202 and task_id."""
        pdf_content = b'%PDF-1.4 fake invoice pdf content'
        data = {
            'invoice_pdf_file': (io.BytesIO(pdf_content), 'MR ASRAFUL ISLAM P I.pdf', 'application/pdf')
        }
        
        response = authenticated_client.post('/process_invoice',
                                             data=data,
                                             content_type='multipart/form-data')
        
        assert response.status_code == 202
        result = response.get_json()
        assert 'task_id' in result


class TestDashboardEndpoint:
    """Tests for /api/dashboard date range filtering."""

    def test_dashboard_with_date_range(self, authenticated_client, mock_sheets_db, monkeypatch):
        """Test getting dashboard with date range query parameter."""
        monkeypatch.setattr('app.workspace_admin_id_for', lambda u: 1)
        mock_sheets_db.get_workspace_dashboard.return_value = {
            'total_claims': 5,
            'pending_claims': 2,
            'completed_claims': 3,
            'new_appointment': 2,
            'inspection_pending': 0,
            'documents_awaited': 0,
            'report_under_preparation': 0,
            'report_submitted': 1,
            'closed': 2,
            'total_invoiced': 1500.0,
            'amount_received': 1000.0,
            'outstanding_fees': 500.0,
            'overdue_count': 0
        }

        response = authenticated_client.get('/api/dashboard?range=1m')
        assert response.status_code == 200
        data = response.get_json()
        assert data['total_claims'] == 5
        mock_sheets_db.get_workspace_dashboard.assert_called_with(1, date_range='1m')

    def test_extract_fee_pdf_no_file(self, authenticated_client):
        """Test extract fee PDF with no file uploaded returns 400."""
        response = authenticated_client.post('/api/extract_fee_pdf', data={})
        assert response.status_code == 400

    def test_admin_backup_download(self, authenticated_client, mock_sheets_db, monkeypatch):
        """Test admin backup snapshot download endpoint."""
        monkeypatch.setattr('app.is_admin_user', lambda u: True)
        mock_sheets_db.get_workspace_reports_page.return_value = {'items': []}
        mock_sheets_db.get_workspace_fee_bills.return_value = []
        
        response = authenticated_client.get('/api/admin/backup/download')
        assert response.status_code == 200
        assert response.mimetype == 'application/json'
        assert b'backup_timestamp' in response.data


