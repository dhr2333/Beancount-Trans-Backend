import pytest
from unittest.mock import patch
from django.contrib.auth.models import User
from django.core.cache import cache
from rest_framework.test import APIClient

from project.apps.authentication.models import UserProfile


@pytest.mark.django_db
class TestEmailAuthentication:
    """邮箱验证码认证测试"""

    def setup_method(self):
        self.client = APIClient()
        cache.clear()
        self.user = User.objects.create_user(
            username='emailuser',
            password='TestPass123!',
            email='email@example.com'
        )

    def test_send_email_code_success(self):
        """测试发送邮箱验证码成功"""
        with patch('django.core.mail.send_mail') as mock_send_mail:
            mock_send_mail.return_value = 1

            response = self.client.post('/api/auth/email/send-code/', {
                'email': 'email@example.com'
            })

            assert response.status_code == 200
            assert '验证码已发送' in response.data['message']
            mock_send_mail.assert_called_once()

    def test_send_email_code_nonexistent_email(self):
        """测试未注册邮箱发送验证码"""
        response = self.client.post('/api/auth/email/send-code/', {
            'email': 'unknown@example.com'
        })

        assert response.status_code == 400
        assert '尚未注册' in str(response.data)

    def test_login_by_code_success(self):
        """测试邮箱验证码登录成功"""
        code = '123456'
        UserProfile.store_email_code(self.user.email, code)

        response = self.client.post('/api/auth/email/login-by-code/', {
            'email': 'email@example.com',
            'code': code
        })

        assert response.status_code == 200
        assert 'access' in response.data
        assert response.data['user']['username'] == 'emailuser'

    def test_login_by_code_wrong_code(self):
        """测试邮箱验证码登录失败（错误验证码）"""
        UserProfile.store_email_code(self.user.email, '123456')

        response = self.client.post('/api/auth/email/login-by-code/', {
            'email': 'email@example.com',
            'code': '654321'
        })

        assert response.status_code == 401
        assert '验证码错误' in str(response.data)

