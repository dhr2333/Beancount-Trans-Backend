"""刷新令牌的滑动续期与 Web 端兼容性测试。

背景：后端开启了 `ROTATE_REFRESH_TOKENS`（每次刷新签发新的 refresh，实现滑动续期），
同时保持 `BLACKLIST_AFTER_ROTATION=False`，因为 Web 端刷新后只保存 access、不保存新的
refresh——旧 refresh 必须继续可用，否则 Web 端会在第一次刷新后被强制登出。
"""
from datetime import timedelta

import pytest
from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

REFRESH_URL = '/api/auth/token/refresh/'


@pytest.mark.django_db
class TestTokenRefresh:
    """刷新接口：轮换 refresh、延长有效期、旧 refresh 仍可用"""

    def setup_method(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='refresh_user', password='pass12345')

        # 模拟「一天前签发」的 refresh，便于验证滑动续期确实延长了有效期
        issued_at = timezone.now() - timedelta(days=1)
        token = RefreshToken.for_user(self.user)
        token.set_exp(
            from_time=issued_at,
            lifetime=settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'],
        )
        self.refresh = str(token)

    def _refresh(self, token):
        return self.client.post(REFRESH_URL, {'refresh': token}, format='json')

    def test_refresh_returns_access_and_new_refresh(self):
        """刷新返回 access 与新的 refresh（轮换）"""
        response = self._refresh(self.refresh)

        assert response.status_code == 200
        assert response.data['access']
        assert response.data['refresh'] != self.refresh

    def test_refresh_slides_expiration(self):
        """新 refresh 的有效期被顺延（滑动续期）"""
        response = self._refresh(self.refresh)
        assert response.status_code == 200

        new_exp = RefreshToken(response.data['refresh']).payload['exp']
        expected = timezone.now() + settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME']

        assert new_exp > RefreshToken(self.refresh).payload['exp']
        assert abs(new_exp - expected.timestamp()) < 60

    def test_old_refresh_still_usable(self):
        """未启用拉黑：旧 refresh 仍可继续刷新（保证 Web 端不被登出）"""
        assert self._refresh(self.refresh).status_code == 200
        assert self._refresh(self.refresh).status_code == 200

    def test_invalid_refresh_is_rejected(self):
        """无效 refresh 返回 401，客户端据此判定登录失效"""
        assert self._refresh('not-a-valid-token').status_code == 401
