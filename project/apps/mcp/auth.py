"""MCP 鉴权：校验平台签发的访问令牌（个人访问令牌 / OAuth 2.1 访问令牌）。"""
from __future__ import annotations

import logging

from asgiref.sync import sync_to_async
from mcp.server.auth.provider import AccessToken

from project.apps.authentication.models import PersonalAccessToken

logger = logging.getLogger(__name__)


def _verify_pat(raw_token: str) -> AccessToken | None:
    """校验个人访问令牌。"""
    token = PersonalAccessToken.authenticate(raw_token)
    if token is None:
        return None

    token.touch()
    logger.info('MCP 请求认证通过（PAT）: user=%s token=%s…', token.user.username, token.prefix)
    return AccessToken(
        token=raw_token,
        client_id='pat',
        scopes=token.scope_list,
        expires_at=int(token.expires_at.timestamp()) if token.expires_at else None,
        subject=str(token.user.pk),
    )


def _verify_oauth(raw_token: str) -> AccessToken | None:
    """校验 OAuth 2.1 访问令牌（django-oauth-toolkit 签发）。"""
    from oauth2_provider.models import AccessToken as OAuthAccessToken

    token = (
        OAuthAccessToken.objects.select_related('user', 'application')
        .filter(token=raw_token)
        .first()
    )
    if token is None or token.is_expired():
        return None
    if token.user is None or not token.user.is_active:
        return None

    logger.info(
        'MCP 请求认证通过（OAuth）: user=%s client=%s',
        token.user.username,
        getattr(token.application, 'name', None) or token.application_id,
    )
    return AccessToken(
        token=raw_token,
        client_id=str(token.application_id or 'oauth'),
        scopes=[scope for scope in (token.scope or '').split() if scope],
        expires_at=int(token.expires.timestamp()) if token.expires else None,
        subject=str(token.user.pk),
    )


def _verify(raw_token: str) -> AccessToken | None:
    """按 PAT、OAuth 顺序校验令牌（Django ORM 为同步实现，需在线程中执行）。"""
    return _verify_pat(raw_token) or _verify_oauth(raw_token)


class PlatformTokenVerifier:
    """实现 mcp SDK 的 TokenVerifier 协议。"""

    async def verify_token(self, token: str) -> AccessToken | None:
        return await sync_to_async(_verify, thread_sensitive=True)(token)
