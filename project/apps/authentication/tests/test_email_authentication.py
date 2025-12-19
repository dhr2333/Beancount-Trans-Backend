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

    def test_send_code_rate_limit(self):
        """测试发送验证码频率限制"""
        with patch('django.core.mail.send_mail') as mock_send_mail:
            mock_send_mail.return_value = 1

            # 第一次发送应该成功
            response = self.client.post('/api/auth/email/send-code/', {
                'email': 'email@example.com'
            })
            assert response.status_code == 200

            # 立即再次发送应该失败
            response = self.client.post('/api/auth/email/send-code/', {
                'email': 'email@example.com'
            })
            assert response.status_code == 400
            assert '发送过于频繁' in str(response.data)

    def test_send_code_invalid_email(self):
        """测试无效邮箱格式"""
        response = self.client.post('/api/auth/email/send-code/', {
            'email': 'invalid-email'
        })

        assert response.status_code == 400

    def test_login_by_code_expired(self):
        """测试验证码过期"""
        # 存储验证码但不立即使用，等待过期
        # 注意：这里需要模拟时间或者使用较短的过期时间
        code = '123456'
        UserProfile.store_email_code(self.user.email, code)

        # 模拟缓存过期（删除验证码）
        from django.core.cache import cache
        cache_key = UserProfile.get_email_code_cache_key(self.user.email)
        cache.delete(cache_key)

        response = self.client.post('/api/auth/email/login-by-code/', {
            'email': 'email@example.com',
            'code': code
        })

        assert response.status_code == 401
        assert '验证码错误或已过期' in str(response.data)

    def test_login_by_code_requires_2fa(self):
        """测试登录时返回2FA状态"""
        from django_otp.plugins.otp_totp.models import TOTPDevice

        # 启用TOTP
        self.user.profile.totp_enabled = True
        device = TOTPDevice.objects.create(
            user=self.user,
            name='default',
            confirmed=True,
            key='JBSWY3DPEHPK3PXP'
        )
        self.user.profile.totp_device_id = device.id
        self.user.profile.save()

        code = '123456'
        UserProfile.store_email_code(self.user.email, code)

        response = self.client.post('/api/auth/email/login-by-code/', {
            'email': 'email@example.com',
            'code': code
        })

        assert response.status_code == 200
        assert 'requires_2fa' in response.data
        assert response.data['requires_2fa'] is True

    def test_login_by_code_multiple_users_same_email(self):
        """测试多个用户使用相同邮箱"""
        # 创建另一个用户，使用相同邮箱
        user2 = User.objects.create_user(
            username='emailuser2',
            password='TestPass123!',
            email='email@example.com'  # 相同邮箱
        )

        code = '123456'
        UserProfile.store_email_code('email@example.com', code)

        response = self.client.post('/api/auth/email/login-by-code/', {
            'email': 'email@example.com',
            'code': code
        })

        # 应该登录第一个匹配的用户
        assert response.status_code == 200
        assert 'access' in response.data

