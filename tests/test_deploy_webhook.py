import hmac
import hashlib
import json
import pytest
from unittest.mock import patch

class TestDeployWebhook:
    """Tests for GitHub Auto-Deploy Webhook."""

    def test_deploy_webhook_missing_signature(self, client):
        response = client.post('/api/deploy-webhook', data=json.dumps({'ref': 'refs/heads/main'}), content_type='application/json')
        assert response.status_code == 403
        data = response.get_json()
        assert 'Missing signature' in data.get('error', '')

    def test_deploy_webhook_invalid_signature(self, client):
        response = client.post(
            '/api/deploy-webhook',
            data=json.dumps({'ref': 'refs/heads/main'}),
            content_type='application/json',
            headers={'X-Hub-Signature-256': 'sha256=invalid_hash_value'}
        )
        assert response.status_code == 403
        data = response.get_json()
        assert 'Invalid signature' in data.get('error', '')

    def test_deploy_webhook_valid_signature_triggers_deploy(self, client):
        secret = "test-deploy-secret-key"
        payload = json.dumps({'ref': 'refs/heads/main', 'after': '8e33443'}).encode('utf-8')
        sig = "sha256=" + hmac.new(secret.encode('utf-8'), payload, hashlib.sha256).hexdigest()

        with patch('os.getenv', side_effect=lambda k, d=None: secret if k == 'DEPLOY_WEBHOOK_SECRET' else d):
            with patch('subprocess.Popen') as mock_popen:
                response = client.post(
                    '/api/deploy-webhook',
                    data=payload,
                    content_type='application/json',
                    headers={'X-Hub-Signature-256': sig}
                )
                assert response.status_code == 200
                data = response.get_json()
                assert data.get('status') == 'Deployment triggered successfully'
                mock_popen.assert_called_once()

    def test_app_version_injected_in_context(self, app):
        with app.test_request_context('/'):
            context_processors = app.template_context_processors[None]
            version_val = None
            for cp in context_processors:
                res = cp()
                if 'app_version' in res:
                    version_val = res['app_version']
                    break
            assert version_val is not None
            assert len(version_val) > 0
