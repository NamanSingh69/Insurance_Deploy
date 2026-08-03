"""
Additional automated integration tests for app factory pattern,
ownership verification, rate limiting, and database search.
"""
import pytest
from unittest.mock import MagicMock, patch
from flask import Flask
from app import create_app

def test_app_factory_creation():
    """Verify create_app creates a valid Flask app with correct config."""
    mock_db = MagicMock()
    app = create_app(db_adapter=mock_db)
    assert isinstance(app, Flask)
    assert app.config['DB_ADAPTER'] == mock_db

def test_unauthenticated_gemini_upload_rejection(client):
    """Verify unauthenticated users are rejected from getting a Gemini upload URL."""
    # Logout/anonymous client
    response = client.post('/get_gemini_upload_url', json={
        'filename': 'test.pdf',
        'mime_type': 'application/pdf',
        'size': 1000
    })
    # Should redirect to login or return 401
    assert response.status_code in [302, 401]

def test_authenticated_gemini_upload_retired(authenticated_client, mock_sheets_db):
    """Verify signed-in users receive 410 GONE when attempting retired client upload route."""
    response = authenticated_client.post('/get_gemini_upload_url', json={
        'filename': 'invoice.pdf',
        'mime_type': 'application/pdf',
        'size': 5000000
    })
    assert response.status_code == 410

def test_cross_user_denial_for_job_status(authenticated_client, mock_sheets_db):
    """Verify user cannot view job status of a job they do not own."""
    # Mock database to return a job owned by user '999'
    mock_sheets_db.get_job_for_user.return_value = None
    
    response = authenticated_client.get('/process_pdf/status/job-abc')
    # Should fail with 404 or 403
    assert response.status_code in [403, 404]

def test_cross_user_denial_for_download(authenticated_client, mock_sheets_db):
    """Verify user cannot download report output they do not own."""
    # Mock database to return a job owned by user '999'
    mock_sheets_db.get_job_by_request_id.return_value = {
        'id': 'job-123',
        'user_id': '999',
        'status': 'completed'
    }
    
    response = authenticated_client.get('/download/report_pdf/req-123')
    assert response.status_code in [403, 404]

def test_cross_user_denial_for_photo_retrieval(authenticated_client, mock_sheets_db):
    """Verify user cannot retrieve asset content they do not own."""
    mock_sheets_db.get_asset_for_user.return_value = None
    
    response = authenticated_client.get('/assets/asset-xyz/content')
    assert response.status_code in [403, 404]

def test_database_search_pagination_contracts(mock_sheets_db):
    """Verify mock sheets_db pagination helper works correctly."""
    result = mock_sheets_db.get_user_reports_page('1', 'john', 1, 50)
    assert 'items' in result
    assert 'page' in result
    assert 'page_size' in result
    assert 'total' in result

def test_teardown_appcontext_closes_db_connection(app, mock_sheets_db):
    """Verify teardown_appcontext invokes close_scoped_connection on db_adapter."""
    mock_sheets_db.close_scoped_connection.reset_mock()
    with app.app_context():
        pass
    mock_sheets_db.close_scoped_connection.assert_called()




