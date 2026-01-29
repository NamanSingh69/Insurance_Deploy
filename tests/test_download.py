
import io
import pytest
from app import generated_data_store

class TestDownloadFileEndpoint:
    """Tests for /download endpoint."""
    
    def test_download_file_success(self, authenticated_client):
        """Test successful file download from memory store."""
        # Reset store just in case
        generated_data_store.clear()
        
        # Inject data structure expected by app.py:
        # data['pdf_report'] should be bytes (not stream, app wraps it in BytesIO)
        # data['report_no'] used for filename
        generated_data_store['test-id'] = {
            'pdf_report': b'fake pdf content',
            'report_no': 'TestReport-001'
        }
        
        # URL uses 'report_pdf' as file_type
        response = authenticated_client.get('/download/report_pdf/test-id')
        
        # Debug output if fails
        if response.status_code != 200:
            print(f"Response status: {response.status_code}")
            print(f"Response data: {response.data}")
            
        assert response.status_code == 200
        assert response.data == b'fake pdf content'
        assert 'application/pdf' in response.content_type
        # check filename in headers?
        # Content-Disposition: attachment; filename=TestReport-001.pdf
        assert b'TestReport-001.pdf' in response.headers.get('Content-Disposition', '').encode()
            
    def test_download_file_not_found(self, authenticated_client):
        """Test download expired or invalid ID."""
        response = authenticated_client.get('/download/report_pdf/nonexistent-id')
        assert response.status_code == 404
