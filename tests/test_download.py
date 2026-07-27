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

    def test_upload_signature_and_status(self, authenticated_client):
        """Test uploading a signature image and checking signature status."""
        # 1. Status initially
        status_res = authenticated_client.get('/signature_status')
        assert status_res.status_code == 200
        
        # 2. Upload fake image
        data = {
            'signature': (io.BytesIO(b'fake png image data'), 'test_signature.png')
        }
        upload_res = authenticated_client.post('/upload_signature', data=data, content_type='multipart/form-data')
        assert upload_res.status_code == 200
        json_data = upload_res.get_json()
        assert json_data['success'] is True
        assert '/static/signature.png' in json_data['url']

        # 3. Status after upload
        status_res2 = authenticated_client.get('/signature_status')
        assert status_res2.status_code == 200
        json_data2 = status_res2.get_json()
        assert json_data2['has_signature'] is True
