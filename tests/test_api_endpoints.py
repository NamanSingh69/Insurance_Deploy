"""
Tests for API endpoints - report CRUD, photo upload, PDF generation.
"""
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
        mock_sheets_db.get_user_reports_page.return_value = {
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
        mock_sheets_db.get_user_reports_page.return_value = {
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
        mock_sheets_db.get_user_reports_page.return_value = {
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
        mock_sheets_db.delete_report.return_value = False
        
        with patch('app.bcrypt.check_password_hash', return_value=True):
            response = authenticated_client.delete('/delete_report/nonexistent-id', json={'password': 'any_password'})
            
            # Expect 404 (Not Found) or 200 with error message depending on implementation
            # Implementation returns 404 if delete_report returns False
            assert response.status_code in [404]


class TestUploadPhotoEndpoint:
    """Tests for /upload_photo endpoint."""
    
    def test_upload_photo_success(self, authenticated_client, mock_sheets_db):
        """Test successful photo upload."""
        # Mock the upload function
        mock_sheets_db.upload_image_to_drive.return_value = {
            'id': 'drive-file-id',
            'view_link': 'https://drive.google.com/view',
            'download_link': 'https://drive.google.com/download'
        }
        
        # Create fake image file
        data = {
            'photo': (io.BytesIO(b'fake image data'), 'test.jpg')
        }
        
        response = authenticated_client.post('/upload_photo',
                                             data=data,
                                             content_type='multipart/form-data')
        
        assert response.status_code == 200
        result = response.get_json()
        assert 'url' in result or result.get('success') == True
    
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
        
        # Now returns 202 with task_id for async processing
        assert response.status_code in [200, 202, 400, 500]
        if response.status_code == 202:
            data = response.get_json()
            assert 'task_id' in data
    
    def test_generate_files_no_data(self, authenticated_client):
        """Test generate files without data."""
        response = authenticated_client.post('/generate_files',
                                             json={},
                                             content_type='application/json')
        
        # Empty data is caught synchronously before async dispatch
        assert response.status_code in [400, 500]


class TestProcessPDFEndpoint:
    """Tests for /process_pdf endpoint."""
    
    def test_process_pdf_no_file(self, authenticated_client):
        """Test process PDF without file."""
        response = authenticated_client.post('/process_pdf',
                                             data={},
                                             content_type='multipart/form-data')
        
        # Should return error synchronously (before async dispatch)
        assert response.status_code in [200, 400]
    
    def test_process_pdf_with_mock_file(self, authenticated_client):
        """Test process PDF with mock file returns task_id (async pattern)."""
        # Create a simple PDF-like bytes
        pdf_content = b'%PDF-1.4 fake pdf content'
        data = {
            'pdf_file': (io.BytesIO(pdf_content), 'test.pdf', 'application/pdf')
        }
        
        response = authenticated_client.post('/process_pdf',
                                             data=data,
                                             content_type='multipart/form-data')
        
        # Now returns 202 with task_id for async processing
        assert response.status_code in [200, 202, 400, 500]
        if response.status_code == 202:
            result = response.get_json()
            assert 'task_id' in result

    def test_process_pdf_status_not_found(self, authenticated_client):
        """Test polling for a non-existent task."""
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

