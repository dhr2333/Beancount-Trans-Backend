import pytest
from unittest.mock import patch, MagicMock
from django.contrib.auth.models import User
from django.core.cache import cache
from rest_framework.test import APIClient
from project.apps.authentication.models import UserProfile


@pytest.mark.django_db
class TestTwoFactorAuth:
    """双因素认证测试"""
    
    def setup_method(self):
        """设置测试环境"""
        self.client = APIClient()
        cache.clear()
        
        self.user = User.objects.create_user(
            username='testuser',
            password='TestPass123!',
            email='test@example.com'
        )
        self.user.profile.phone_number = '+8613800138040'
        self.user.profile.phone_verified = True
        self.user.profile.save()
    
    def test_2fa_status_disabled(self):
        """测试获取2FA状态（未启用）"""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.get('/api/auth/2fa/status/')
        
        assert response.status_code == 200
        assert response.data['totp_enabled'] is False
        assert response.data['has_2fa'] is False
    
    def test_2fa_status_enabled(self):
        """测试获取2FA状态（已启用）"""
        from django_otp.plugins.otp_totp.models import TOTPDevice
        
        device = TOTPDevice.objects.create(
            user=self.user,
            name='default',
            confirmed=True,
            key='JBSWY3DPEHPK3PXP'
        )
        self.user.profile.totp_enabled = True
        self.user.profile.totp_device_id = device.id
        self.user.profile.save()
        
        self.client.force_authenticate(user=self.user)
        
        response = self.client.get('/api/auth/2fa/status/')
        
        assert response.status_code == 200
        assert response.data['totp_enabled'] is True
        assert response.data['has_2fa'] is True
    
    def test_totp_qrcode_success(self):
        """测试生成TOTP二维码成功"""
        from django_otp.plugins.otp_totp.models import TOTPDevice
        
        self.client.force_authenticate(user=self.user)
        
        response = self.client.get('/api/auth/2fa/totp/qrcode/')
        
        assert response.status_code == 200
        assert 'qr_code' in response.data
        assert 'secret' in response.data
        assert 'device_id' in response.data
        assert response.data['qr_code'].startswith('data:image/png;base64,')
        
        # 验证设备已创建
        assert TOTPDevice.objects.filter(user=self.user).exists()
        # 验证profile已更新
        self.user.profile.refresh_from_db()
        assert self.user.profile.totp_device_id is not None
    
    def test_totp_qrcode_already_enabled(self):
        """测试TOTP已启用时生成二维码"""
        from django_otp.plugins.otp_totp.models import TOTPDevice
        
        device = TOTPDevice.objects.create(
            user=self.user,
            name='default',
            confirmed=True,
            key='JBSWY3DPEHPK3PXP'
        )
        self.user.profile.totp_enabled = True
        self.user.profile.totp_device_id = device.id
        self.user.profile.save()
        
        self.client.force_authenticate(user=self.user)
        
        response = self.client.get('/api/auth/2fa/totp/qrcode/')
        
        assert response.status_code == 400
        assert 'TOTP已启用，请先禁用' in response.data['error']
    
    def test_totp_enable_success(self):
        """测试启用TOTP成功"""
        from django_otp.plugins.otp_totp.models import TOTPDevice
        from unittest.mock import patch, MagicMock
        
        # 先生成二维码
        device = TOTPDevice.objects.create(
            user=self.user,
            name='default',
            confirmed=False,
            key='JBSWY3DPEHPK3PXP'
        )
        self.user.profile.totp_device_id = device.id
        self.user.profile.save()
        
        self.client.force_authenticate(user=self.user)
        
        # Mock TOTP验证 - 由于视图会重新查询设备，需要mock objects.get()返回的对象
        with patch('django_otp.plugins.otp_totp.models.TOTPDevice.objects.get') as mock_get:
            # 创建一个mock设备，设置verify_token方法
            mock_device = MagicMock()
            mock_device.verify_token.return_value = True
            mock_device.id = device.id
            mock_device.user = self.user
            mock_device.confirmed = False
            mock_get.return_value = mock_device
            
            response = self.client.post('/api/auth/2fa/totp/enable/', {
                'code': '123456'
            })
            
            assert response.status_code == 200
            assert 'TOTP启用成功' in response.data['message']
            
            # 验证TOTP已启用
            self.user.profile.refresh_from_db()
            assert self.user.profile.totp_enabled is True
            
            # 验证verify_token被调用
            mock_device.verify_token.assert_called_once_with('123456')
            # 验证设备被保存
            assert mock_device.save.called
            assert mock_device.confirmed is True
    
    def test_totp_enable_wrong_code(self):
        """测试启用TOTP时验证码错误"""
        from django_otp.plugins.otp_totp.models import TOTPDevice
        from unittest.mock import patch, MagicMock
        
        device = TOTPDevice.objects.create(
            user=self.user,
            name='default',
            confirmed=False,
            key='JBSWY3DPEHPK3PXP'
        )
        self.user.profile.totp_device_id = device.id
        self.user.profile.save()
        
        self.client.force_authenticate(user=self.user)
        
        # Mock TOTP验证失败
        with patch('django_otp.plugins.otp_totp.models.TOTPDevice.objects.get') as mock_get:
            mock_device = MagicMock()
            mock_device.verify_token.return_value = False
            mock_device.id = device.id
            mock_device.user = self.user
            mock_get.return_value = mock_device
            
            response = self.client.post('/api/auth/2fa/totp/enable/', {
                'code': '123456'
            })
            
            assert response.status_code == 400
            assert '验证码错误' in response.data['error']
            
            # 验证TOTP未启用
            self.user.profile.refresh_from_db()
            assert self.user.profile.totp_enabled is False
    
    def test_totp_enable_no_device(self):
        """测试没有设备时启用TOTP"""
        self.client.force_authenticate(user=self.user)
        
        # 不创建设备
        self.user.profile.totp_device_id = None
        self.user.profile.save()
        
        response = self.client.post('/api/auth/2fa/totp/enable/', {
            'code': '123456'
        })
        
        assert response.status_code == 400
        assert '请先生成TOTP二维码' in response.data['error']
    
    def test_totp_disable_success(self):
        """测试禁用TOTP成功"""
        from django_otp.plugins.otp_totp.models import TOTPDevice
        from unittest.mock import patch, MagicMock
        
        device = TOTPDevice.objects.create(
            user=self.user,
            name='default',
            confirmed=True,
            key='JBSWY3DPEHPK3PXP'
        )
        self.user.profile.totp_enabled = True
        self.user.profile.totp_device_id = device.id
        self.user.profile.save()
        
        self.client.force_authenticate(user=self.user)
        
        # Mock TOTP验证
        with patch('django_otp.plugins.otp_totp.models.TOTPDevice.objects.get') as mock_get:
            mock_device = MagicMock()
            mock_device.verify_token.return_value = True
            mock_device.id = device.id
            mock_device.user = self.user
            mock_get.return_value = mock_device
            
            response = self.client.post('/api/auth/2fa/totp/disable/', {
                'code': '123456'
            })
            
            assert response.status_code == 200
            assert 'TOTP禁用成功' in response.data['message']
            
            # 验证TOTP已禁用
            self.user.profile.refresh_from_db()
            assert self.user.profile.totp_enabled is False
            assert self.user.profile.totp_device_id is None
    
    def test_totp_disable_wrong_code(self):
        """测试禁用TOTP时验证码错误"""
        from django_otp.plugins.otp_totp.models import TOTPDevice
        from unittest.mock import patch, MagicMock
        
        device = TOTPDevice.objects.create(
            user=self.user,
            name='default',
            confirmed=True,
            key='JBSWY3DPEHPK3PXP'
        )
        self.user.profile.totp_enabled = True
        self.user.profile.totp_device_id = device.id
        self.user.profile.save()
        
        self.client.force_authenticate(user=self.user)
        
        # Mock TOTP验证失败
        with patch('django_otp.plugins.otp_totp.models.TOTPDevice.objects.get') as mock_get:
            mock_device = MagicMock()
            mock_device.verify_token.return_value = False
            mock_device.id = device.id
            mock_device.user = self.user
            mock_get.return_value = mock_device
            
            response = self.client.post('/api/auth/2fa/totp/disable/', {
                'code': '123456'
            })
            
            assert response.status_code == 400
            assert '验证码错误' in response.data['error']
            
            # 验证TOTP仍然启用
            self.user.profile.refresh_from_db()
            assert self.user.profile.totp_enabled is True
    
    def test_totp_disable_not_enabled(self):
        """测试TOTP未启用时禁用"""
        self.client.force_authenticate(user=self.user)
        
        self.user.profile.totp_enabled = False
        self.user.profile.save()
        
        response = self.client.post('/api/auth/2fa/totp/disable/', {
            'code': '123456'
        })
        
        assert response.status_code == 400
        assert 'TOTP未启用' in response.data['error']

