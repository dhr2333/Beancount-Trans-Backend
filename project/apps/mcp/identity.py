"""MCP 请求身份解析：把访问令牌映射为 Django 用户。"""
from __future__ import annotations

import logging

from django.conf import settings
from django.contrib.auth.models import User
from mcp.server.auth.middleware.auth_context import get_access_token

from project.apps.authentication.models import PersonalAccessToken

logger = logging.getLogger(__name__)


class IdentityError(RuntimeError):
    """无法确定当前请求所属的用户。"""


def _user_from_subject(subject: str) -> User | None:
    try:
        user_id = int(subject)
    except (TypeError, ValueError):
        return None
    return User.objects.filter(pk=user_id, is_active=True).first()


def get_current_user() -> User:
    """返回当前 MCP 请求所属的用户。

    已携带访问令牌时以令牌 subject（用户主键）为准；未携带令牌时回退到
    settings.MCP_DEV_USERNAME 指定的本地开发用户。
    """
    token = get_access_token()
    if token is not None:
        user = _user_from_subject(token.subject or '')
        if user is None:
            logger.warning('MCP 访问令牌 subject 无效: %r', token.subject)
            raise IdentityError('访问令牌对应的用户不存在或已停用')
        return user

    dev_username = getattr(settings, 'MCP_DEV_USERNAME', '')
    if dev_username:
        user = User.objects.filter(username=dev_username, is_active=True).first()
        if user is not None:
            return user
        raise IdentityError(f'MCP_DEV_USERNAME 指定的用户不存在或已停用: {dev_username}')

    raise IdentityError('未提供访问令牌，且未配置 MCP_DEV_USERNAME 本地开发用户')


def get_current_personal_access_token() -> PersonalAccessToken | None:
    """返回当前 MCP 请求对应的个人访问令牌；OAuth 或开发态返回 None。"""
    token = get_access_token()
    if token is None or token.client_id != 'pat':
        return None
    return PersonalAccessToken.authenticate(token.token)


def touch_current_personal_access_token() -> None:
    """实际读取账本数据后记录令牌使用时间；非 PAT 请求静默跳过。"""
    pat = get_current_personal_access_token()
    if pat is not None:
        pat.touch()
