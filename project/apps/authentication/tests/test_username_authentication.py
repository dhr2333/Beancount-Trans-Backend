import pytest
from unittest.mock import patch
from django.contrib.auth.models import User
from django.core.cache import cache
from rest_framework.test import APIClient
from project.apps.authentication.models import UserProfile


@pytest.mark.django_db
class TestUsernameAuthentication:
    """用户名/邮箱+密码认证测试"""

    def setup_method(self):
        """设置测试环境"""
        self.client = APIClient()
        cache.clear()

    def test_login_by_username_success(self):
        """测试用户名登录成功"""
        user = User.objects.create_user(
            username='testuser',
            password='TestPass123!',
            email='test@example.com'
        )
        user.profile.phone_number = '+8613800138020'
        user.profile.phone_verified = True
        user.profile.save()

        response = self.client.post('/api/auth/username/login-by-password/', {
            'username': 'testuser',
            'password': 'TestPass123!'
        })

        assert response.status_code == 200
        assert 'access' in response.data
        assert response.data['user']['username'] == 'testuser'

    def test_login_by_email_success(self):
        """测试邮箱登录成功"""
        user = User.objects.create_user(
            username='testuser2',
            password='TestPass123!',
            email='test2@example.com'
        )
        user.profile.phone_number = '+8613800138021'
        user.profile.phone_verified = True
        user.profile.save()

        response = self.client.post('/api/auth/username/login-by-password/', {
            'username': 'test2@example.com',
            'password': 'TestPass123!'
        })

        assert response.status_code == 200
        assert 'access' in response.data
        assert response.data['user']['username'] == 'testuser2'

    def test_login_with_totp_success(self):
        """测试用户名登录+TOTP验证成功"""
        from unittest.mock import patch, MagicMock
        from django_otp.plugins.otp_totp.models import TOTPDevice

        user = User.objects.create_user(
            username='testuser3',
            password='TestPass123!',
            email='test3@example.com'
        )
        user.profile.phone_number = '+8613800138022'
        user.profile.phone_verified = True
        user.profile.totp_enabled = True

        device = TOTPDevice.objects.create(
            user=user,
            name='default',
            confirmed=True,
            key='JBSWY3DPEHPK3PXP'
        )
        user.profile.totp_device_id = device.id
        user.profile.save()

        # Mock TOTP验证
        with patch('django_otp.plugins.otp_totp.models.TOTPDevice.objects.get') as mock_get:
            mock_device = MagicMock()
            mock_device.verify_token.return_value = True
            mock_device.id = device.id
            mock_device.user = user
            mock_get.return_value = mock_device

            response = self.client.post('/api/auth/username/login-by-password/', {
                'username': 'testuser3',
                'password': 'TestPass123!',
                'totp_code': '123456'
            })

            assert response.status_code == 200
            assert 'access' in response.data

    def test_login_with_totp_missing(self):
        """测试启用TOTP但未提供验证码"""
        from django_otp.plugins.otp_totp.models import TOTPDevice

        user = User.objects.create_user(
            username='testuser4',
            password='TestPass123!',
            email='test4@example.com'
        )
        user.profile.phone_number = '+8613800138023'
        user.profile.phone_verified = True
        user.profile.totp_enabled = True

        device = TOTPDevice.objects.create(
            user=user,
            name='default',
            confirmed=True,
            key='JBSWY3DPEHPK3PXP'
        )
        user.profile.totp_device_id = device.id
        user.profile.save()

        response = self.client.post('/api/auth/username/login-by-password/', {
            'username': 'testuser4',
            'password': 'TestPass123!'
            # 不提供totp_code
        })

        assert response.status_code == 400
        assert 'TOTP二次验证' in response.data['error']
        assert response.data['requires_totp'] is True

    def test_login_with_totp_wrong(self):
        """测试TOTP验证码错误"""
        from unittest.mock import patch, MagicMock
        from django_otp.plugins.otp_totp.models import TOTPDevice

        user = User.objects.create_user(
            username='testuser5',
            password='TestPass123!',
            email='test5@example.com'
        )
        user.profile.phone_number = '+8613800138024'
        user.profile.phone_verified = True
        user.profile.totp_enabled = True

        device = TOTPDevice.objects.create(
            user=user,
            name='default',
            confirmed=True,
            key='JBSWY3DPEHPK3PXP'
        )
        user.profile.totp_device_id = device.id
        user.profile.save()

        # Mock TOTP验证失败
        with patch('django_otp.plugins.otp_totp.models.TOTPDevice.objects.get') as mock_get:
            mock_device = MagicMock()
            mock_device.verify_token.return_value = False
            mock_device.id = device.id
            mock_device.user = user
            mock_get.return_value = mock_device

            response = self.client.post('/api/auth/username/login-by-password/', {
                'username': 'testuser5',
                'password': 'TestPass123!',
                'totp_code': '123456'
            })

            assert response.status_code == 400
            assert 'TOTP验证码错误' in response.data['error']

    def test_login_wrong_password(self):
        """测试密码错误"""
        user = User.objects.create_user(
            username='testuser6',
            password='TestPass123!',
            email='test6@example.com'
        )
        user.profile.phone_number = '+8613800138025'
        user.profile.phone_verified = True
        user.profile.save()

        response = self.client.post('/api/auth/username/login-by-password/', {
            'username': 'testuser6',
            'password': 'WrongPassword'
        })

        assert response.status_code == 401
        assert '用户名/邮箱或密码错误' in response.data['error']

    def test_login_user_not_found(self):
        """测试用户不存在"""
        response = self.client.post('/api/auth/username/login-by-password/', {
            'username': 'nonexistent',
            'password': 'TestPass123!'
        })

        assert response.status_code == 401
        assert '用户名/邮箱或密码错误' in response.data['error']

    def test_login_user_without_profile(self):
        """测试用户没有Profile（自动创建）"""
        user = User.objects.create_user(
            username='testuser7',
            password='TestPass123!',
            email='test7@example.com'
        )
        # 删除profile（如果存在）
        if hasattr(user, 'profile'):
            user.profile.delete()

        response = self.client.post('/api/auth/username/login-by-password/', {
            'username': 'testuser7',
            'password': 'TestPass123!'
        })

        # 应该能登录（中间件会拦截未绑定手机号的用户）
        assert response.status_code == 200
        # 验证profile已自动创建
        user.refresh_from_db()
        assert hasattr(user, 'profile')

