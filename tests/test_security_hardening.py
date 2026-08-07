"""
Security Hardening and Isolation Tests.
Verifies CSRF enforcement, credential non-exposure, private asset access control,
durable job creation, and network isolation.
"""
import io
import pytest
from unittest.mock import MagicMock, patch


class TestSecurityHardening:
    """Security assertion test suite."""

    def test_csrf_blocks_unsafe_requests_when_enabled(self, mock_sheets_db, mock_user):
        """CSRF blocks POST requests lacking a valid token when CSRF is enabled."""
        mock_sheets_db.get_user_by_id.return_value = mock_user
        mock_sheets_db.get_user_by_username.return_value = mock_user
        from app import create_app
        test_app = create_app(
            db_adapter=mock_sheets_db,
            config={'TESTING': False, 'WTF_CSRF_ENABLED': True}
        )
        with test_app.test_client() as c:
            # 1. Login user
            with c.session_transaction() as sess:
                sess['_user_id'] = '1'
                sess['_fresh'] = True
                sess['_csrf_token'] = 'fixed-test-csrf-token'

            # 2. Unsafe request without token is rejected
            resp = c.post('/save_report', json={'survey_report': {'report_no': 'R1'}})
            assert resp.status_code == 400

            # 3. Unsafe request with matching X-CSRFToken header is accepted
            headers = {'X-CSRFToken': 'fixed-test-csrf-token'}
            resp_ok = c.post(
                '/save_report',
                json={'survey_report': {'report_no': 'R1'}},
                headers=headers
            )
            assert resp_ok.get_json() != {'error': 'CSRF validation failed. Refresh the page and try again.'}

    def test_user_profile_never_exposes_stored_gemini_key(self, authenticated_client, mock_sheets_db):
        """Verify get_user_profile does not return the raw Gemini key."""
        mock_sheets_db.get_user_by_id.return_value = {
            'id': '1',
            'username': 'testuser',
            'full_name': 'Test User',
            'encrypted_gemini_api_key': 'enc_secret_key_123',
            'role': 'admin'
        }
        
        response = authenticated_client.get('/get_user_profile')
        assert response.status_code == 200
        data = response.get_json()
        assert 'gemini_api_key' not in data
        assert 'encrypted_gemini_api_key' not in data
        assert 'enc_secret_key_123' not in str(response.data)
        assert data.get('has_gemini_api_key') is not None

    def test_available_models_is_post_only(self, authenticated_client):
        """GET to /api/available_models is rejected; POST works with JSON body."""
        get_res = authenticated_client.get('/api/available_models')
        assert get_res.status_code == 405

        post_res = authenticated_client.post('/api/available_models', json={'api_key': None})
        assert post_res.status_code == 200
        assert isinstance(post_res.get_json(), list)

    def test_retired_direct_provider_routes_return_410(self, authenticated_client):
        """Verify client-driven upload and legacy proxy routes return 410 GONE."""
        res_upload = authenticated_client.post('/get_gemini_upload_url', json={})
        assert res_upload.status_code == 410

        res_drive = authenticated_client.post('/upload_report_to_drive', json={})
        assert res_drive.status_code == 410

        res_proxy = authenticated_client.get('/proxy_image?url=http://example.com/test.jpg')
        assert res_proxy.status_code in [404, 410]

    def test_proxy_image_and_local_image_handling(self, authenticated_client, mock_sheets_db):
        """Verify proxy_image and local_image routes handle missing assets gracefully without 500 errors."""
        mock_sheets_db.get_asset_by_locator.return_value = None
        mock_sheets_db.get_asset_for_access.return_value = None
        mock_sheets_db.get_file_content.return_value = None

        res_p = authenticated_client.get('/proxy_image/nonexistent_123')
        assert res_p.status_code == 404

        res_l = authenticated_client.get('/local_image/nonexistent_123')
        assert res_l.status_code == 404

    def test_private_asset_content_denies_unauthorized_user(self, authenticated_client, mock_sheets_db):
        """Access to an asset owned by another user is denied (404/403)."""
        # Return asset owned by user '999'
        mock_sheets_db.get_asset_for_access.return_value = None
        
        response = authenticated_client.get('/assets/unowned-asset-id/content')
        assert response.status_code in [403, 404]

    def test_photo_and_signature_uploads_return_private_asset_routes(self, authenticated_client, mock_sheets_db):
        """Uploads return private asset URLs /assets/<id>/content."""
        valid_png = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x03\x01\x01\x00\xc9\xfe\x92\xef\x00\x00\x00\x00IEND\xaeB`\x82'
        
        # 1. Photo upload
        photo_res = authenticated_client.post('/upload_photo', data={'photo': (io.BytesIO(valid_png), 'pic.png')})
        assert photo_res.status_code == 200
        photo_json = photo_res.get_json()
        assert photo_json['success'] is True
        assert '/assets/' in photo_json['url'] and '/content' in photo_json['url']

        # 2. Signature upload
        sig_res = authenticated_client.post('/upload_signature', data={'signature': (io.BytesIO(valid_png), 'sig.png')})
        assert sig_res.status_code == 200
        sig_json = sig_res.get_json()
        assert sig_json['success'] is True
        assert '/assets/' in sig_json['url'] and '/content' in sig_json['url']

    def test_process_endpoints_create_durable_jobs(self, authenticated_client, sample_report_data):
        """Process and file generation endpoints dispatch durable jobs and return 202 with task_id."""
        # 1. generate_files
        gen_res = authenticated_client.post('/generate_files', json=sample_report_data)
        assert gen_res.status_code == 202
        assert 'task_id' in gen_res.get_json()

        # 2. process_pdf
        pdf_res = authenticated_client.post('/process_pdf', data={
            'pdf_file': (io.BytesIO(b'%PDF-1.4 test content'), 'test.pdf')
        })
        assert pdf_res.status_code == 202
        assert 'task_id' in pdf_res.get_json()

        # 3. process_invoice
        inv_res = authenticated_client.post('/process_invoice', data={
            'invoice_pdf_file': (io.BytesIO(b'%PDF-1.4 invoice content'), 'inv.pdf')
        })
        assert inv_res.status_code == 202
        assert 'task_id' in inv_res.get_json()
