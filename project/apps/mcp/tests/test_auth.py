"""MCP 令牌校验器测试：个人访问令牌（PAT）与 OAuth 2.1 访问令牌双通道。"""
import asyncio
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone
from mcp.server.auth.provider import AccessToken as McpAccessToken
from oauth2_provider.models import AccessToken as OAuthAccessToken
from oauth2_provider.models import Application

from project.apps.authentication.models import PersonalAccessToken
from project.apps.mcp.auth import PlatformTokenVerifier
from project.apps.mcp.identity import (
    get_current_personal_access_token,
    touch_current_personal_access_token,
)

pytestmark = pytest.mark.django_db(transaction=True)


def _verify(raw_token):
    return asyncio.run(PlatformTokenVerifier().verify_token(raw_token))


@pytest.fixture
def pat(user):
    return PersonalAccessToken.issue(user, 'MCP 单元测试')


@pytest.fixture
def oauth_application(user):
    return Application.objects.create(
        name='MCP 单元测试客户端',
        user=user,
        client_type=Application.CLIENT_PUBLIC,
        authorization_grant_type=Application.GRANT_AUTHORIZATION_CODE,
        redirect_uris='http://127.0.0.1/callback',
    )


def _issue_oauth_token(user, application, **overrides):
    defaults = {
        'user': user,
        'application': application,
        'token': 'oauth-raw-token',
        'expires': timezone.now() + timedelta(hours=1),
        'scope': 'ledger:read',
    }
    defaults.update(overrides)
    return OAuthAccessToken.objects.create(**defaults)


class TestPersonalAccessTokenChannel:
    def test_accepts_valid_token(self, user, pat):
        record, raw_token = pat
        token = _verify(raw_token)
        assert token is not None
        assert token.client_id == 'pat'
        assert token.subject == str(user.pk)
        assert token.scopes == ['ledger:read']
        assert token.expires_at is None

    def test_does_not_record_last_used_at_on_verification(self, pat):
        record, raw_token = pat
        assert record.last_used_at is None
        _verify(raw_token)
        record.refresh_from_db()
        assert record.last_used_at is None

    def test_rejects_revoked_token(self, pat):
        record, raw_token = pat
        record.revoked_at = timezone.now()
        record.save(update_fields=['revoked_at'])
        assert _verify(raw_token) is None

    def test_rejects_expired_token(self, user):
        _, raw_token = PersonalAccessToken.issue(
            user, '过期令牌', expires_at=timezone.now() - timedelta(seconds=1)
        )
        assert _verify(raw_token) is None

    def test_accepts_token_with_future_expiry(self, user):
        expires_at = timezone.now() + timedelta(days=30)
        _, raw_token = PersonalAccessToken.issue(user, '未过期令牌', expires_at=expires_at)
        token = _verify(raw_token)
        assert token is not None
        assert token.expires_at == int(expires_at.timestamp())

    def test_rejects_token_of_inactive_user(self, user, pat):
        _, raw_token = pat
        user.is_active = False
        user.save(update_fields=['is_active'])
        assert _verify(raw_token) is None


class TestOAuthChannel:
    def test_accepts_valid_token(self, user, oauth_application):
        record = _issue_oauth_token(user, oauth_application)
        token = _verify(record.token)
        assert token is not None
        assert token.subject == str(user.pk)
        assert token.scopes == ['ledger:read']
        assert token.client_id == str(oauth_application.pk)
        assert token.expires_at == int(record.expires.timestamp())

    def test_splits_multiple_scopes(self, user, oauth_application):
        record = _issue_oauth_token(user, oauth_application, scope='ledger:read ledger:write')
        assert _verify(record.token).scopes == ['ledger:read', 'ledger:write']

    def test_rejects_expired_token(self, user, oauth_application):
        record = _issue_oauth_token(
            user, oauth_application, expires=timezone.now() - timedelta(seconds=1)
        )
        assert _verify(record.token) is None

    def test_rejects_token_of_inactive_user(self, user, oauth_application):
        record = _issue_oauth_token(user, oauth_application)
        user.is_active = False
        user.save(update_fields=['is_active'])
        assert _verify(record.token) is None

    def test_rejects_deleted_token(self, user, oauth_application):
        record = _issue_oauth_token(user, oauth_application)
        raw_token = record.token
        record.delete()
        assert _verify(raw_token) is None


class TestUnknownTokens:
    @pytest.mark.parametrize(
        'raw_token',
        ['', 'random-token', 'bct_tooshort', 'bct_' + 'f' * 8 + 'nonexistent'],
    )
    def test_rejects_unknown_format(self, raw_token):
        assert _verify(raw_token) is None


class TestCurrentPersonalAccessToken:
    def _access_token(self, record, raw_token, client_id='pat'):
        return McpAccessToken(
            token=raw_token,
            client_id=client_id,
            scopes=['ledger:read'],
            expires_at=None,
            subject=str(record.user_id),
        )

    def test_resolves_pat_from_current_access_token(self, pat):
        record, raw_token = pat
        access_token = self._access_token(record, raw_token)

        with patch(
            'project.apps.mcp.identity.get_access_token', return_value=access_token
        ):
            resolved = get_current_personal_access_token()

        assert resolved is not None
        assert resolved.pk == record.pk

    def test_ignores_non_pat_client(self, pat):
        record, raw_token = pat
        access_token = self._access_token(record, raw_token, client_id='oauth-app')

        with patch(
            'project.apps.mcp.identity.get_access_token', return_value=access_token
        ):
            assert get_current_personal_access_token() is None

    def test_touch_updates_last_used_at(self, pat):
        record, raw_token = pat
        access_token = self._access_token(record, raw_token)

        with patch(
            'project.apps.mcp.identity.get_access_token', return_value=access_token
        ):
            touch_current_personal_access_token()

        record.refresh_from_db()
        assert record.last_used_at is not None
