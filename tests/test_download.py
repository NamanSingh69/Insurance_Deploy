import io
import pytest
from app import generated_data_store

class TestDownloadFileEndpoint:
    """Tests for /download endpoint."""
    
    def test_download_file_success(self, authenticated_client):
        """Test successful file download from memory store."""
        generated_data_store.clear()
        
        generated_data_store['test-id'] = {
            'pdf_report': b'fake pdf content',
            'report_no': 'TestReport-001',
            'user_id': '1'
        }
        
        response = authenticated_client.get('/download/report_pdf/test-id')
        
        assert response.status_code == 200
        assert response.data == b'fake pdf content'
        assert 'application/pdf' in response.content_type
        assert b'TestReport-001.pdf' in response.headers.get('Content-Disposition', '').encode()
            
    def test_download_file_not_found(self, authenticated_client, mock_sheets_db):
        """Test download expired or invalid ID."""
        mock_sheets_db.get_job_by_request_id.return_value = None
        mock_sheets_db.get_report_by_id.return_value = None
        response = authenticated_client.get('/download/report_pdf/nonexistent-id')
        assert response.status_code == 404
