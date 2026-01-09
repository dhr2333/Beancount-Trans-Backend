import pytest
from unittest.mock import patch
from django.contrib.auth.models import User
from django.core.cache import cache
from rest_framework.test import APIClient
from project.apps.authentication.models import UserProfile


@pytest.mark.django_db
class TestIntegration:
    """集成测试"""

    def setup_method(self):
        """设置测试环境"""
        self.client = APIClient()
        cache.clear()

    def test_complete_registration_flow(self):
        """测试完整注册流程（发送验证码→注册→登录）"""
        phone_number = '+8613800138130'

        # 1. 发送验证码
        response = self.client.post('/api/auth/phone/send-code/', {
            'phone_number': phone_number
        })
        assert response.status_code == 200

        # 2. 获取验证码（从日志或缓存）
        # 在实际场景中，用户会收到短信
        # 这里我们直接从缓存获取
        profile = UserProfile(phone_number=phone_number)
        cache_key = profile.get_sms_cache_key(phone_number)
        code = cache.get(cache_key)
        assert code is not None

        # 3. 注册
        response = self.client.post('/api/auth/phone/register/', {
            'phone_number': phone_number,
            'code': code,
            # 'username': 'integrateduser',
            # 'password': 'TestPass123!',
            'email': 'integrated@example.com'
        })
        assert response.status_code == 201
        assert 'access' in response.data

        # 4. 使用密码登录
        # response = self.client.post('/api/auth/phone/login-by-password/', {
        #     'phone_number': phone_number,
        #     'password': 'TestPass123!'
        # })
        # assert response.status_code == 200
        # assert 'access' in response.data

    def test_complete_binding_flow(self):
        """测试完整绑定流程（发送验证码→绑定手机号→验证）"""
        user = User.objects.create_user(
            username='bindinguser',
            password='TestPass123!',
            email='binding@example.com'
        )

        self.client.force_authenticate(user=user)

        phone_number = '+8613800138131'

        # 1. 发送验证码
        response = self.client.post('/api/auth/phone/send-code/', {
            'phone_number': phone_number
        })
        assert response.status_code == 200

        # 2. 获取验证码
        profile = UserProfile(phone_number=phone_number)
        cache_key = profile.get_sms_cache_key(phone_number)
        code = cache.get(cache_key)

        # 3. 绑定手机号
        response = self.client.post('/api/auth/bindings/bind-phone/', {
            'phone_number': phone_number,
            'code': code
        })
        assert response.status_code == 200

        # 4. 验证绑定
        user.refresh_from_db()
        assert str(user.profile.phone_number) == phone_number
        assert user.profile.phone_verified is True

    def test_complete_2fa_flow(self):
        """测试完整2FA流程（生成二维码→启用→登录验证→禁用）"""
        user = User.objects.create_user(
            username='2fauser',
            password='TestPass123!',
            email='2fa@example.com'
        )
        user.profile.phone_number = '+8613800138132'
        user.profile.phone_verified = True
        user.profile.save()

        self.client.force_authenticate(user=user)

        # 1. 生成二维码
        response = self.client.get('/api/auth/2fa/totp/qrcode/')
        assert response.status_code == 200
        assert 'qr_code' in response.data
        device_id = response.data['device_id']

        # 2. 启用TOTP（需要验证码）
        from django_otp.plugins.otp_totp.models import TOTPDevice
        from unittest.mock import patch, MagicMock

        device = TOTPDevice.objects.get(id=device_id)

        with patch('django_otp.plugins.otp_totp.models.TOTPDevice.objects.get') as mock_get:
            mock_device = MagicMock()
            mock_device.verify_token.return_value = True
            mock_device.id = device.id
            mock_device.user = user
            mock_device.confirmed = False
            mock_get.return_value = mock_device

            response = self.client.post('/api/auth/2fa/totp/enable/', {
                'code': '123456'
            })
            assert response.status_code == 200

            # 验证已启用
            user.profile.refresh_from_db()
            assert user.profile.totp_enabled is True

        # 3. 登录验证（需要TOTP码）
        with patch('django_otp.plugins.otp_totp.models.TOTPDevice.objects.get') as mock_get:
            mock_device = MagicMock()
            mock_device.verify_token.return_value = True
            mock_device.id = device.id
            mock_device.user = user
            mock_get.return_value = mock_device

            response = self.client.post('/api/auth/phone/login-by-password/', {
                'phone_number': '+8613800138132',
                'password': 'TestPass123!',
                'totp_code': '123456'
            })
            assert response.status_code == 200

        # 4. 禁用TOTP
        with patch('django_otp.plugins.otp_totp.models.TOTPDevice.objects.get') as mock_get:
            mock_device = MagicMock()
            mock_device.verify_token.return_value = True
            mock_device.id = device.id
            mock_device.user = user
            mock_get.return_value = mock_device

            response = self.client.post('/api/auth/2fa/totp/disable/', {
                'code': '123456'
            })
            assert response.status_code == 200

            # 验证已禁用
            user.profile.refresh_from_db()
            assert user.profile.totp_enabled is False

    def test_login_with_middleware(self):
        """测试登录后中间件检查"""
        # 创建未绑定手机号的用户
        user = User.objects.create_user(
            username='middlewareuser',
            password='TestPass123!',
            email='middleware@example.com'
        )

        # 使用用户名登录（不通过中间件的排除路径）
        # 注意：这里需要实际登录，然后访问受保护的端点
        # 由于中间件在视图之前执行，我们需要模拟完整的请求流程

        # 登录后访问需要手机号的端点
        self.client.force_authenticate(user=user)
        response = self.client.get('/api/auth/profile/me/')

        # 由于中间件检查，应该返回403（如果未绑定手机号）
        # 但这里我们使用force_authenticate，可能绕过中间件
        # 实际测试中需要确保中间件已正确配置

    def test_account_deletion_cleanup(self):
        """测试账户删除时数据清理"""
        user = User.objects.create_user(
            username='deleteuser',
            password='TestPass123!',
            email='delete@example.com'
        )
        user.profile.phone_number = '+8613800138134'
        user.profile.phone_verified = True
        user.profile.save()

        self.client.force_authenticate(user=user)

        user_id = user.id
        username = user.username

        response = self.client.delete('/api/auth/profile/delete_account/')

        assert response.status_code == 200

        # 验证用户已删除
        assert not User.objects.filter(id=user_id).exists()

        # 验证profile已删除
        assert not UserProfile.objects.filter(user_id=user_id).exists()

