"""MCP 服务装配配置测试：鉴权开关与传输层安全设置。"""
import pytest

from project.apps.mcp.server import _auth_settings, _transport_security

pytestmark = pytest.mark.django_db(transaction=True)


class TestAuthSettings:
    def test_disabled_returns_none(self, settings, monkeypatch):
        monkeypatch.setattr(settings, 'MCP_AUTH_ENABLED', False)
        monkeypatch.setattr(settings, 'MCP_RESOURCE_SERVER_URL', 'https://example.com/mcp')
        assert _auth_settings() is None

    def test_missing_resource_url_returns_none(self, settings, monkeypatch):
        monkeypatch.setattr(settings, 'MCP_AUTH_ENABLED', True)
        monkeypatch.setattr(settings, 'MCP_RESOURCE_SERVER_URL', '')
        assert _auth_settings() is None

    def test_issuer_defaults_to_resource_url(self, settings, monkeypatch):
        monkeypatch.setattr(settings, 'MCP_AUTH_ENABLED', True)
        monkeypatch.setattr(settings, 'MCP_RESOURCE_SERVER_URL', 'https://example.com/mcp')
        monkeypatch.setattr(settings, 'MCP_ISSUER_URL', '')
        auth = _auth_settings()
        assert str(auth.issuer_url) == 'https://example.com/mcp'
        assert str(auth.resource_server_url) == 'https://example.com/mcp'
        assert auth.required_scopes == ['ledger:read']

    def test_issuer_can_be_overridden(self, settings, monkeypatch):
        monkeypatch.setattr(settings, 'MCP_AUTH_ENABLED', True)
        monkeypatch.setattr(settings, 'MCP_RESOURCE_SERVER_URL', 'https://example.com/mcp')
        monkeypatch.setattr(settings, 'MCP_ISSUER_URL', 'https://auth.example.com')
        auth = _auth_settings()
        assert str(auth.issuer_url).rstrip('/') == 'https://auth.example.com'

    def test_resource_indicator_validation_disabled(self, settings, monkeypatch):
        monkeypatch.setattr(settings, 'MCP_AUTH_ENABLED', True)
        monkeypatch.setattr(settings, 'MCP_RESOURCE_SERVER_URL', 'https://example.com/mcp')
        assert _auth_settings().validate_token_resource is False


class TestTransportSecurity:
    def test_uses_configured_allowlists(self, settings, monkeypatch):
        monkeypatch.setattr(settings, 'MCP_ALLOWED_HOSTS', ['example.com:38001'])
        monkeypatch.setattr(settings, 'MCP_ALLOWED_ORIGINS', ['http://example.com:38001'])
        security = _transport_security()
        assert security.enable_dns_rebinding_protection is True
        assert security.allowed_hosts == ['example.com:38001']
        assert security.allowed_origins == ['http://example.com:38001']

    def test_falls_back_to_loopback(self, settings, monkeypatch):
        monkeypatch.setattr(settings, 'MCP_ALLOWED_HOSTS', [])
        monkeypatch.setattr(settings, 'MCP_ALLOWED_ORIGINS', [])
        security = _transport_security()
        assert 'localhost:*' in security.allowed_hosts
        assert 'http://localhost:*' in security.allowed_origins
