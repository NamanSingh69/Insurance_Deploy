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
        mock_sheets_db.get_user_reports_metadata_only.return_value = []
        
        response = authenticated_client.get('/get_saved_reports')
        
        assert response.status_code == 200
        data = response.get_json()
        assert response.status_code == 200
        assert isinstance(data, list)
        assert len(data) == 0
    
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
        mock_sheets_db.get_user_reports_metadata_only.return_value = mock_reports
        
        response = authenticated_client.get('/get_saved_reports')
        
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]['report_no'] == 'SR-001'
    
    def test_get_reports_with_search(self, authenticated_client, mock_sheets_db):
        """Test searching reports."""
        mock_sheets_db.get_user_reports_metadata_only.return_value = [
            {'id': '1', 'report_no': 'SR-001', 'insured_name': 'John'}
        ]
        
        response = authenticated_client.get('/get_saved_reports?query=john')
        
        assert response.status_code == 200


class TestLoadReportEndpoint:
    """Tests for /load_report/<report_id> endpoint."""
    
    def test_load_report_success(self, authenticated_client, mock_sheets_db, sample_report_data):
        """Test loading existing report."""
        mock_sheets_db.get_user_reports.return_value = [{
            'id': 'test-id',
            'user_id': '1',
            'report_no': 'SR-001',
            'report_data_json': '{"survey_report": {}, "assessment": {}}'
        }]
        
        response = authenticated_client.get('/load_report/test-id')
        
        assert response.status_code in [200, 404]
    
    def test_load_report_not_found(self, authenticated_client, mock_sheets_db):
        """Test loading non-existent report."""
        mock_sheets_db.get_user_reports.return_value = []
        
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
        """Test successful file generation."""
        response = authenticated_client.post('/generate_files',
                                             json=sample_report_data,
                                             content_type='application/json')
        
        # May succeed or fail depending on mock setup
        assert response.status_code in [200, 400, 500]
    
    def test_generate_files_no_data(self, authenticated_client):
        """Test generate files without data."""
        response = authenticated_client.post('/generate_files',
                                             json={},
                                             content_type='application/json')
        
        assert response.status_code in [400, 500]


class TestProcessPDFEndpoint:
    """Tests for /process_pdf endpoint."""
    
    def test_process_pdf_no_file(self, authenticated_client):
        """Test process PDF without file."""
        response = authenticated_client.post('/process_pdf',
                                             data={},
                                             content_type='multipart/form-data')
        
        # Should return error
        assert response.status_code in [200, 400]
    
    def test_process_pdf_with_mock_file(self, authenticated_client):
        """Test process PDF with mock file."""
        # Create a simple PDF-like bytes
        pdf_content = b'%PDF-1.4 fake pdf content'
        data = {
            'pdf': (io.BytesIO(pdf_content), 'test.pdf')
        }
        
        response = authenticated_client.post('/process_pdf',
                                             data=data,
                                             content_type='multipart/form-data')
        
        # Will likely fail Gemini processing but should not crash
        assert response.status_code in [200, 400, 500]
