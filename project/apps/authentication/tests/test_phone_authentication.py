import pytest
from django.contrib.auth.models import User
from django.core.cache import cache
from rest_framework.test import APIClient
from project.apps.authentication.models import UserProfile


@pytest.mark.django_db
class TestPhoneAuthentication:
    """手机号认证测试"""

    def setup_method(self):
        """设置测试环境"""
        self.client = APIClient()
        cache.clear()

    # def test_send_sms_code(self):
    #     """测试发送验证码"""
    #     response = self.client.post('/api/auth/phone/send-code/', {
    #         'phone_number': '+8613800138000'
    #     })
    #     assert response.status_code == 200
    #     assert '验证码已发送' in response.data['message']

    def test_send_sms_code_rate_limit(self):
        """测试验证码发送频率限制"""
        phone_number = '+8613800138001'

        # 第一次发送应该成功
        response = self.client.post('/api/auth/phone/send-code/', {
            'phone_number': phone_number
        })
        assert response.status_code == 200

        # 立即再次发送应该失败
        response = self.client.post('/api/auth/phone/send-code/', {
            'phone_number': phone_number
        })
        assert response.status_code == 400
        assert '发送过于频繁' in response.data['error']

    def test_register_with_phone(self):
        """测试手机号注册"""
        phone_number = '+8613800138002'

        # 先存储验证码到缓存（模拟发送验证码）
        profile = UserProfile(phone_number=phone_number)
        profile.store_sms_code('123456', phone_number)

        # 注册
        response = self.client.post('/api/auth/phone/register/', {
            'phone_number': phone_number,
            'code': '123456',
            'username': 'testuser',
            'password': 'TestPass123!',
            'email': 'test@example.com'
        })

        assert response.status_code == 201
        assert 'access' in response.data
        assert response.data['user']['username'] == 'testuser'

        # 验证用户已创建
        user = User.objects.get(username='testuser')
        assert user.profile.phone_number == phone_number
        assert user.profile.phone_verified is True

    def test_login_by_code(self):
        """测试验证码登录"""
        # 创建用户
        user = User.objects.create_user(username='testuser2', password='TestPass123!')
        profile = user.profile
        profile.phone_number = '+8613800138003'
        profile.phone_verified = True
        profile.save()

        # 存储验证码
        profile.store_sms_code('654321', profile.phone_number)

        # 登录
        response = self.client.post('/api/auth/phone/login-by-code/', {
            'phone_number': '+8613800138003',
            'code': '654321'
        })

        assert response.status_code == 200
        assert 'access' in response.data
        assert response.data['user']['username'] == 'testuser2'

    def test_login_by_password(self):
        """测试密码登录"""
        # 创建用户
        user = User.objects.create_user(username='testuser3', password='TestPass123!')
        profile = user.profile
        profile.phone_number = '+8613800138004'
        profile.save()

        # 登录
        response = self.client.post('/api/auth/phone/login-by-password/', {
            'phone_number': '+8613800138004',
            'password': 'TestPass123!'
        })

        assert response.status_code == 200
        assert 'access' in response.data
        assert response.data['user']['username'] == 'testuser3'

    def test_login_with_wrong_password(self):
        """测试错误密码登录"""
        # 创建用户
        user = User.objects.create_user(username='testuser4', password='TestPass123!')
        profile = user.profile
        profile.phone_number = '+8613800138005'
        profile.save()

        # 使用错误密码登录
        response = self.client.post('/api/auth/phone/login-by-password/', {
            'phone_number': '+8613800138005',
            'password': 'WrongPassword'
        })

        assert response.status_code == 401

    def test_register_without_username_generation(self):
        """测试注册时自动生成用户名"""
        phone_number = '+8613800138010'
        profile = UserProfile(phone_number=phone_number)
        profile.store_sms_code('123456', phone_number)

        response = self.client.post('/api/auth/phone/register/', {
            'phone_number': phone_number,
            'code': '123456',
            'password': 'TestPass123!',
            'email': 'test@example.com'
            # 不提供用户名
        })

        assert response.status_code == 201
        assert 'access' in response.data
        assert 'user' in response.data
        assert response.data['user']['username'].startswith('user_')

    def test_register_duplicate_username(self):
        """测试注册时用户名冲突处理"""
        phone_number = '+8613800138011'
        profile = UserProfile(phone_number=phone_number)
        profile.store_sms_code('123456', phone_number)

        # 先创建一个用户
        User.objects.create_user(username='testuser5', password='TestPass123!')

        # 尝试使用相同用户名注册
        response = self.client.post('/api/auth/phone/register/', {
            'phone_number': phone_number,
            'code': '123456',
            'username': 'testuser5',
            'password': 'TestPass123!'
        })

        assert response.status_code == 400
        assert '用户名已存在' in str(response.data)

    def test_register_without_password(self):
        """测试注册时不设置密码"""
        phone_number = '+8613800138012'
        profile = UserProfile(phone_number=phone_number)
        profile.store_sms_code('123456', phone_number)

        response = self.client.post('/api/auth/phone/register/', {
            'phone_number': phone_number,
            'code': '123456',
            'username': 'testuser6',
            'email': 'test@example.com'
            # 不提供密码
        })

        assert response.status_code == 201
        user = User.objects.get(username='testuser6')
        assert not user.has_usable_password()

    def test_login_by_code_requires_2fa(self):
        """测试验证码登录时返回2FA状态"""
        user = User.objects.create_user(username='testuser7', password='TestPass123!')
        profile = user.profile
        profile.phone_number = '+8613800138013'
        profile.phone_verified = True
        profile.totp_enabled = True
        profile.save()

        profile.store_sms_code('654321', profile.phone_number)

        response = self.client.post('/api/auth/phone/login-by-code/', {
            'phone_number': '+8613800138013',
            'code': '654321'
        })

        assert response.status_code == 200
        assert 'requires_2fa' in response.data
        assert response.data['requires_2fa'] is True

    def test_login_by_password_with_totp(self):
        """测试密码登录时TOTP验证成功"""
        from unittest.mock import patch, MagicMock
        from django_otp.plugins.otp_totp.models import TOTPDevice

        user = User.objects.create_user(username='testuser8', password='TestPass123!')
        profile = user.profile
        profile.phone_number = '+8613800138014'
        profile.totp_enabled = True

        # 创建TOTP设备
        device = TOTPDevice.objects.create(
            user=user,
            name='default',
            confirmed=True,
            key='JBSWY3DPEHPK3PXP'
        )
        profile.totp_device_id = device.id
        profile.save()

        # Mock TOTP验证 - 需要mock objects.get()
        with patch('django_otp.plugins.otp_totp.models.TOTPDevice.objects.get') as mock_get:
            mock_device = MagicMock()
            mock_device.verify_token.return_value = True
            mock_device.id = device.id
            mock_device.user = user
            mock_get.return_value = mock_device

            response = self.client.post('/api/auth/phone/login-by-password/', {
                'phone_number': '+8613800138014',
                'password': 'TestPass123!',
                'totp_code': '123456'
            })

            assert response.status_code == 200
            assert 'access' in response.data

    def test_login_by_password_with_totp_missing(self):
        """测试密码登录时缺少TOTP码"""
        from django_otp.plugins.otp_totp.models import TOTPDevice

        user = User.objects.create_user(username='testuser9', password='TestPass123!')
        profile = user.profile
        profile.phone_number = '+8613800138015'
        profile.totp_enabled = True

        device = TOTPDevice.objects.create(
            user=user,
            name='default',
            confirmed=True,
            key='JBSWY3DPEHPK3PXP'
        )
        profile.totp_device_id = device.id
        profile.save()

        response = self.client.post('/api/auth/phone/login-by-password/', {
            'phone_number': '+8613800138015',
            'password': 'TestPass123!'
            # 不提供totp_code
        })

        assert response.status_code == 400
        assert 'TOTP二次验证' in response.data['error']
        assert response.data['requires_totp'] is True

    def test_login_by_password_with_totp_wrong(self):
        """测试密码登录时TOTP验证码错误"""
        from unittest.mock import patch, MagicMock
        from django_otp.plugins.otp_totp.models import TOTPDevice

        user = User.objects.create_user(username='testuser10', password='TestPass123!')
        profile = user.profile
        profile.phone_number = '+8613800138016'
        profile.totp_enabled = True

        device = TOTPDevice.objects.create(
            user=user,
            name='default',
            confirmed=True,
            key='JBSWY3DPEHPK3PXP'
        )
        profile.totp_device_id = device.id
        profile.save()

        # Mock TOTP验证失败
        with patch('django_otp.plugins.otp_totp.models.TOTPDevice.objects.get') as mock_get:
            mock_device = MagicMock()
            mock_device.verify_token.return_value = False
            mock_device.id = device.id
            mock_device.user = user
            mock_get.return_value = mock_device

            response = self.client.post('/api/auth/phone/login-by-password/', {
                'phone_number': '+8613800138016',
                'password': 'TestPass123!',
                'totp_code': '123456'
            })

            assert response.status_code == 400
            assert 'TOTP验证码错误' in response.data['error']

    def test_login_by_password_with_totp_device_not_found(self):
        """测试密码登录时TOTP设备不存在"""
        user = User.objects.create_user(username='testuser11', password='TestPass123!')
        profile = user.profile
        profile.phone_number = '+8613800138017'
        profile.totp_enabled = True
        profile.totp_device_id = 99999  # 不存在的设备ID
        profile.save()

        response = self.client.post('/api/auth/phone/login-by-password/', {
            'phone_number': '+8613800138017',
            'password': 'TestPass123!',
            'totp_code': '123456'
        })

        assert response.status_code == 400
        assert 'TOTP设备不存在' in response.data['error']

