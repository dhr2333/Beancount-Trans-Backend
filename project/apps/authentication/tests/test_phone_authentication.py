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
        """测试手机号注册（用户名和密码自动生成）"""
        phone_number = '+8613800138002'

        # 先存储验证码到缓存（模拟发送验证码）
        profile = UserProfile(phone_number=phone_number)
        profile.store_sms_code('123456', phone_number)

        # 注册（不再支持用户名和密码字段）
        response = self.client.post('/api/auth/phone/register/', {
            'phone_number': phone_number,
            'code': '123456',
            'email': 'test@example.com'
        })

        assert response.status_code == 201
        assert 'access' in response.data
        # 用户名应该自动生成，格式为手机号数字（如 13800138002）
        username = response.data['user']['username']
        assert username.isdigit() or '_' in username  # 纯数字或带后缀

        # 验证用户已创建
        username = response.data['user']['username']
        user = User.objects.get(username=username)
        assert user.profile.phone_number == phone_number
        assert user.profile.phone_verified is True
        assert not user.has_usable_password()  # 密码应该为空

    def test_login_by_code(self):
        """测试验证码登录（已注册用户）"""
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

    def test_login_by_code_auto_register(self):
        """测试验证码登录自动注册（未注册用户）"""
        phone_number = '+8613800140000'
        
        # 存储验证码（但用户不存在）
        profile = UserProfile(phone_number=phone_number)
        profile.store_sms_code('888888', phone_number)
        
        # 验证码登录（应该自动注册）
        response = self.client.post('/api/auth/phone/login-by-code/', {
            'phone_number': phone_number,
            'code': '888888'
        })
        
        assert response.status_code == 200
        assert 'access' in response.data
        assert 'user' in response.data
        # 用户名应该自动生成，格式为手机号数字（如 13800140000）
        username = response.data['user']['username']
        assert username.isdigit() or '_' in username  # 纯数字或带后缀
        
        # 验证用户已创建
        user = User.objects.get(username=username)
        assert user.profile.phone_number == phone_number
        assert user.profile.phone_verified is True
        assert not user.has_usable_password()  # 密码应该为空

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

    def test_register_username_auto_generation(self):
        """测试注册时自动生成用户名"""
        phone_number = '+8613800138010'
        profile = UserProfile(phone_number=phone_number)
        profile.store_sms_code('123456', phone_number)

        response = self.client.post('/api/auth/phone/register/', {
            'phone_number': phone_number,
            'code': '123456',
            'email': 'test@example.com'
        })

        assert response.status_code == 201
        assert 'access' in response.data
        assert 'user' in response.data
        # 用户名应该自动生成，格式为手机号数字（如 13800138010）
        username = response.data['user']['username']
        assert username.isdigit() or '_' in username  # 纯数字或带后缀

    def test_register_username_conflict_handling(self):
        """测试注册时用户名冲突自动处理（生成唯一用户名）"""
        phone_number = '+8613800138011'
        profile = UserProfile(phone_number=phone_number)
        profile.store_sms_code('123456', phone_number)

        # 先创建一个用户，使用可能冲突的用户名
        User.objects.create_user(username='user_13800138011', password='TestPass123!')

        # 注册时应该自动生成不冲突的用户名
        response = self.client.post('/api/auth/phone/register/', {
            'phone_number': phone_number,
            'code': '123456'
        })

        assert response.status_code == 201
        # 用户名应该与已存在的不同
        username = response.data['user']['username']
        assert username != '13800138011'
        # 如果冲突，应该有后缀；如果不冲突，应该是纯数字
        assert username.isdigit() or '_' in username  # 纯数字或带后缀

    def test_register_no_password_by_default(self):
        """测试注册时默认不设置密码"""
        phone_number = '+8613800138012'
        profile = UserProfile(phone_number=phone_number)
        profile.store_sms_code('123456', phone_number)

        response = self.client.post('/api/auth/phone/register/', {
            'phone_number': phone_number,
            'code': '123456',
            'email': 'test@example.com'
        })

        assert response.status_code == 201
        username = response.data['user']['username']
        user = User.objects.get(username=username)
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

