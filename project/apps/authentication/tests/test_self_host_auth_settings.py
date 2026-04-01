"""自托管相关认证配置（与 settings 模块加载时读取的环境变量一致，测试中通过 override_settings 模拟）"""

import pytest
from django.contrib.auth.models import User
from django.test import override_settings
from rest_framework.test import APIClient


_SELF_HOST_BACKENDS = [
    'project.apps.authentication.backends.PhonePasswordBackend',
    'project.apps.authentication.backends.PhoneCodeBackend',
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]


@pytest.mark.django_db
class TestSelfHostUsernameLoginWithoutPhone:
    @override_settings(AUTHENTICATION_BACKENDS=_SELF_HOST_BACKENDS)
    def test_username_login_without_verified_phone(self):
        """PHONE_BINDING_REQUIRED=False 时等价后端链：未验证手机号的用户可用用户名密码登录"""
        client = APIClient()
        user = User.objects.create_user(
            username='nophone',
            password='TestPass123!',
            email='nophone@example.com',
        )
        profile = user.profile
        profile.phone_verified = False
        profile.phone_number = None
        profile.save()

        response = client.post(
            '/api/auth/username/login-by-password/',
            {'username': 'nophone', 'password': 'TestPass123!'},
        )
        assert response.status_code == 200
        assert 'access' in response.data


@pytest.mark.django_db
class TestAuthPublicConfig:
    def test_public_config_ok(self):
        client = APIClient()
        response = client.get('/api/auth/public-config/')
        assert response.status_code == 200
        assert 'phone_binding_required' in response.data
        assert 'sms_enabled' in response.data
        assert isinstance(response.data['phone_binding_required'], bool)
        assert isinstance(response.data['sms_enabled'], bool)


@pytest.mark.django_db
class TestSmsDisabledEndpoints:
    @override_settings(SMS_ENABLED=False)
    def test_send_code_returns_503(self):
        client = APIClient()
        response = client.post(
            '/api/auth/phone/send-code/',
            {'phone_number': '+8613800138000'},
        )
        assert response.status_code == 503
        assert response.data.get('code') == 'SMS_DISABLED'
