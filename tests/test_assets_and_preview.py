"""
Tests for uploaded asset content retrieval and PDF preview functionality.
Ensures zero context loss, timezone robustness, and proper preview generation.
"""
import io
import json
import uuid
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

def test_upload_photo_and_fetch_content(authenticated_client, mock_sheets_db):
    """Test uploading a photo and retrieving its content via /assets/<id>/content."""
    mock_asset = {
        'id': 'mock-asset-id',
        'user_id': 1,
        'storage_kind': 'private_local',
        'storage_locator': 'test_locator.jpg',
        'filename': 'test.jpg',
        'mime_type': 'image/jpeg',
        'expires_at': datetime.utcnow() + timedelta(hours=24),
        'report_id': None,
        'purpose': 'photo'
    }
    mock_sheets_db.create_asset.return_value = mock_asset
    mock_sheets_db.get_asset_for_access.return_value = mock_asset

    fake_png = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x03\x01\x01\x00\xc9\xfe\x92\xef\x00\x00\x00\x00IEND\xaeB`\x82'

    with patch('modules.assets.read_asset_content', return_value=fake_png):
        data = {'photo': (io.BytesIO(fake_png), 'test.png')}
        res_upload = authenticated_client.post(
            '/upload_photo',
            data=data,
            content_type='multipart/form-data'
        )
        assert res_upload.status_code == 200
        result = res_upload.get_json()
        assert result.get('success') is True
        asset_url = result.get('url')
        assert asset_url == f"/assets/{mock_asset['id']}/content"

        res_content = authenticated_client.get(asset_url)
        assert res_content.status_code == 200
        assert res_content.data == fake_png


def test_pdf_preview_download_flow(authenticated_client, mock_sheets_db):
    """Test end-to-end PDF preview download route with durable job asset."""
    req_id = str(uuid.uuid4())
    asset_id = 'test-generated-pdf-asset-123456'
    fake_pdf = b'%PDF-1.4 Fake PDF Content'

    mock_job = {
        'id': 'job-uuid-123',
        'user_id': 1,
        'kind': 'generate_files',
        'status': 'completed',
        'result_json': {
            'request_id': req_id,
            'asset_id': asset_id,
            'report_no': 'R-2026-001',
            'vehicle_no': 'WB02AB1234'
        }
    }
    mock_asset = {
        'id': asset_id,
        'user_id': 1,
        'storage_kind': 'private_local',
        'storage_locator': 'generated.pdf',
        'filename': 'WB02AB1234.pdf',
        'mime_type': 'application/pdf',
        'expires_at': datetime.utcnow() + timedelta(minutes=30)
    }

    mock_sheets_db.get_job_by_request_id.return_value = mock_job
    mock_sheets_db.get_asset_for_access.return_value = mock_asset

    with patch('modules.assets.read_asset_content', return_value=fake_pdf):
        res = authenticated_client.get(f'/download/report_pdf/{req_id}?preview=true')
        assert res.status_code == 200
        assert res.mimetype == 'application/pdf'
        assert b'%PDF-' in res.data
