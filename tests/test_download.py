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
        assert 'signature' in json_data['url']

        # 3. Status after upload
        status_res2 = authenticated_client.get('/signature_status')
        assert status_res2.status_code == 200
        json_data2 = status_res2.get_json()
        assert json_data2['has_signature'] is True

    def test_download_consolidated_csv_new_columns(self, authenticated_client, mock_sheets_db, monkeypatch):
        """Test download consolidated CSV contains Insurer Company Name and Assigned Date columns."""
        monkeypatch.setattr('app.is_admin_user', lambda u: True)
        mock_sheets_db.get_workspace_reports_page.return_value = {
            'items': [{
                'id': 1,
                'saved_at': '2026-08-01T10:00:00',
                'report_data_json': '{"survey_report": {"insured": "John Doe", "insurer": "National Insurance", "policy_no": "POL123", "claim_no": "CLM456", "vehicle_regn_no": "WB01A1234", "report_no": "REP001", "report_date": "2026-08-01"}}'
            }]
        }
        mock_sheets_db.get_workspace_report_by_id.return_value = {
            'id': 1,
            'saved_at': '2026-08-01T10:00:00',
            'report_data_json': '{"survey_report": {"insured": "John Doe", "insurer": "National Insurance", "policy_no": "POL123", "claim_no": "CLM456", "vehicle_regn_no": "WB01A1234", "report_no": "REP001", "report_date": "2026-08-01"}}'
        }
        mock_sheets_db.get_user_reports.return_value = []
        mock_sheets_db.get_workspace_fee_bills.return_value = []
        mock_sheets_db.get_user_fee_bills.return_value = []

        response = authenticated_client.get('/download_consolidated_csv?from_date=2026-08-01&to_date=2026-08-02')
        assert response.status_code == 200
        csv_text = response.data.decode('utf-8')
        headers = csv_text.splitlines()[0].split(',')
        assert "Insurer Company Name" in headers
        assert "Assigned Date" in headers
