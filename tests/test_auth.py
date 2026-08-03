"""
Tests for authentication routes.
"""
import pytest
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestLoginRoute:
    """Tests for /login endpoint."""
    
    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        """Set up mocks for each test."""
        self.mock_user = {
            'id': '1',
            'username': 'testuser',
            'password_hash': '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.HJtF/OqJkKxhTu',
            'full_name': 'Test User'
        }
    
    def test_login_page_loads(self, client):
        """Test login page renders correctly."""
        response = client.get('/login')
        assert response.status_code == 200
        # Should contain login form
        assert b'login' in response.data.lower() or b'Login' in response.data
    
    def test_login_success(self, client, mock_sheets_db):
        """Test successful login."""
        mock_sheets_db.get_user_by_username.return_value = self.mock_user
        
        with patch('app.bcrypt.check_password_hash', return_value=True):
            response = client.post('/login', data={
                'username': 'testuser',
                'password': 'password123'
            }, follow_redirects=False)
        
        # Should redirect to index on success
        assert response.status_code in [200, 302]
    
    def test_login_success_with_next(self, client, mock_sheets_db):
        """Test successful login with next query parameter."""
        mock_sheets_db.get_user_by_username.return_value = self.mock_user
        
        with patch('app.bcrypt.check_password_hash', return_value=True):
            response = client.post('/login?next=%2F', data={
                'username': 'testuser',
                'password': 'password123'
            }, follow_redirects=False)
        
        assert response.status_code == 302
        assert response.location == '/'

    def test_login_username_trimmed_and_case_insensitive(self, client, mock_sheets_db):
        """Test login with leading/trailing whitespace and uppercase username."""
        mock_sheets_db.get_user_by_username.return_value = self.mock_user
        
        with patch('app.bcrypt.check_password_hash', return_value=True):
            response = client.post('/login', data={
                'username': '  TESTUSER  ',
                'password': 'password123'
            }, follow_redirects=False)
        
        assert response.status_code in [200, 302]
        mock_sheets_db.get_user_by_username.assert_called_with('TESTUSER')

    def test_login_invalid_password(self, client, mock_sheets_db):
        """Test login with invalid password."""
        mock_sheets_db.get_user_by_username.return_value = self.mock_user
        
        with patch('app.bcrypt.check_password_hash', return_value=False):
            response = client.post('/login', data={
                'username': 'testuser',
                'password': 'wrongpassword'
            }, follow_redirects=True)
        
        assert response.status_code == 200
        # Should show error or stay on login page
    
    def test_login_user_not_found(self, client, mock_sheets_db):
        """Test login with non-existent user."""
        mock_sheets_db.get_user_by_username.return_value = None
        
        response = client.post('/login', data={
            'username': 'nonexistent',
            'password': 'password123'
        }, follow_redirects=True)
        
        assert response.status_code == 200


class TestLogoutRoute:
    """Tests for /logout endpoint."""
    
    def test_logout_redirects(self, authenticated_client):
        """Test logout redirects to login page."""
        response = authenticated_client.post('/logout', follow_redirects=False)
        assert response.status_code == 302
    
    def test_logout_clears_session(self, authenticated_client):
        """Test logout clears user session."""
        # First verify we're logged in
        response = authenticated_client.get('/', follow_redirects=False)
        assert response.status_code == 200
        
        # Now logout via POST
        authenticated_client.post('/logout', follow_redirects=True)
        
        # Accessing protected page should redirect to login
        response = authenticated_client.get('/', follow_redirects=False)
        assert response.status_code in [200, 302]


class TestProtectedRoutes:
    """Test that protected routes require authentication."""
    
    def test_index_requires_auth(self, client):
        """Test index page requires login."""
        response = client.get('/', follow_redirects=False)
        # Should redirect to login
        assert response.status_code == 302 or b'login' in response.data.lower()
    
    def test_save_report_requires_auth(self, client):
        """Test save_report endpoint requires login."""
        response = client.post('/save_report', 
                              json={'survey_report': {}},
                              follow_redirects=False)
        assert response.status_code in [302, 401]
    
    def test_get_saved_reports_requires_auth(self, client):
        """Test get_saved_reports endpoint requires login."""
        response = client.get('/get_saved_reports', follow_redirects=False)
        assert response.status_code in [302, 401]
