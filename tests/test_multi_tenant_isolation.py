"""
Multi-Tenant Isolation & Localized Sub-User Access Integration Tests.
Verifies independent admin workspaces (SKANOWAR, PRANAYMAITY) and localized sub-user access (USER, USER1).
"""
import json
import pytest
from unittest.mock import MagicMock


def test_independent_admin_tenant_workspaces(client, mock_sheets_db):
    """Test that PRANAYMAITY and SKANOWAR operate independent workspaces with zero cross-tenant bleed."""
    # Mock users
    skanowar_user = {
        'id': '3',
        'username': 'SKANOWAR',
        'role': 'admin',
        'admin_id': None,
        'full_name': 'SK ANOWAR ALI',
        'is_locked': False
    }
    pranay_user = {
        'id': '4',
        'username': 'PRANAYMAITY',
        'role': 'admin',
        'admin_id': None,
        'full_name': 'Pranay Maity',
        'is_locked': False
    }
    
    # Mock workspace reports
    skanowar_report = {
        'id': 'rep-sk-1',
        'user_id': '3',
        'workspace_admin_id': '3',
        'report_no': 'SK/2026/01',
        'claim_no': 'CLM-SK-100',
        'insured_name': 'Sk Client',
        'status': 'report_submitted'
    }
    pranay_report = {
        'id': 'rep-pm-1',
        'user_id': '4',
        'workspace_admin_id': '4',
        'report_no': 'PM/2027/01',
        'claim_no': 'CLM-PM-200',
        'insured_name': 'Pranay Client',
        'status': 'new_appointment'
    }

    # When querying reports as PRANAYMAITY
    def mock_get_workspace_reports(ws_id, query='', page=1, page_size=50, *args, **kwargs):
        if str(ws_id) == '4':
            return {'items': [pranay_report], 'page': 1, 'page_size': 50, 'total': 1}
        elif str(ws_id) == '3':
            return {'items': [skanowar_report], 'page': 1, 'page_size': 50, 'total': 1}
        return {'items': [], 'page': 1, 'page_size': 50, 'total': 0}

    mock_sheets_db.get_workspace_reports_page.side_effect = mock_get_workspace_reports
    mock_sheets_db.get_accessible_reports_page.side_effect = mock_get_workspace_reports
    mock_sheets_db.get_user_by_id.side_effect = lambda uid: pranay_user if str(uid) == '4' else skanowar_user

    # Login as PRANAYMAITY
    with client.session_transaction() as sess:
        sess['_user_id'] = '4'
        sess['_fresh'] = True

    resp = client.get('/api/claims')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['total'] == 1
    assert data['items'][0]['claim_no'] == 'CLM-PM-200'
    assert data['items'][0]['insured_name'] == 'Pranay Client'


def test_employee_user1_localized_access_under_pranay(client, mock_sheets_db):
    """Test that USER1 (employee under PRANAYMAITY) only accesses localized files in Pranay's workspace."""
    user1_employee = {
        'id': '5',
        'username': 'USER1',
        'role': 'employee',
        'admin_id': '4',
        'full_name': 'USER1 Assistant',
        'is_locked': False
    }

    user1_created_report = {
        'id': 'rep-u1-1',
        'user_id': '5',
        'workspace_admin_id': '4',
        'report_no': 'PM/2027/02',
        'claim_no': 'CLM-U1-300',
        'insured_name': 'User1 Staged Client',
        'status': 'new_appointment'
    }

    def mock_get_accessible_reports(ws_id, uid, query='', page=1, page_size=50, role=None, *args, **kwargs):
        assert str(ws_id) == '4'  # Bound to Pranay's workspace
        if role == 'employee' and str(uid) == '5':
            return {'items': [user1_created_report], 'page': 1, 'page_size': 50, 'total': 1}
        return {'items': [], 'page': 1, 'page_size': 50, 'total': 0}

    mock_sheets_db.get_accessible_reports_page.side_effect = mock_get_accessible_reports
    mock_sheets_db.get_user_by_id.return_value = user1_employee

    # Login as USER1
    with client.session_transaction() as sess:
        sess['_user_id'] = '5'
        sess['_fresh'] = True

    resp = client.get('/get_saved_reports')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['total'] == 1
    assert data['items'][0]['claim_no'] == 'CLM-U1-300'

    # USER1 cannot delete reports (403 Forbidden via @admin_required)
    resp_del = client.delete('/delete_report/rep-u1-1', json={'password': 'test'})
    assert resp_del.status_code == 403


def test_employee_cannot_access_other_tenant_workspace_data(client, mock_sheets_db):
    """Test that employee USER (under SKANOWAR) cannot see or access PRANAYMAITY workspace reports."""
    sk_employee = {
        'id': '1',
        'username': 'USER',
        'role': 'employee',
        'admin_id': '3',
        'full_name': 'SK Assistant',
        'is_locked': False
    }

    def mock_get_accessible_reports(ws_id, uid, *args, **kwargs):
        assert str(ws_id) == '3'  # Bound strictly to SKANOWAR workspace
        return {'items': [], 'page': 1, 'page_size': 50, 'total': 0}

    mock_sheets_db.get_accessible_reports_page.side_effect = mock_get_accessible_reports
    mock_sheets_db.get_user_by_id.return_value = sk_employee

    # Login as USER
    with client.session_transaction() as sess:
        sess['_user_id'] = '1'
        sess['_fresh'] = True

    resp = client.get('/get_saved_reports')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['total'] == 0
