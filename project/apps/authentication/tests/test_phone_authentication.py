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
        
    def test_send_sms_code(self):
        """测试发送验证码"""
        response = self.client.post('/api/auth/phone/send-code/', {
            'phone_number': '+8613800138000'
        })
        assert response.status_code == 200
        assert '验证码已发送' in response.data['message']
    
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

    def test_oauth_context_without_session(self):
        """测试未检测到社交登录上下文"""
        response = self.client.get('/api/auth/phone/oauth-context/')
        assert response.status_code == 404

    def test_oauth_register_without_session(self):
        """测试在没有社交登录的情况下注册失败"""
        response = self.client.post('/api/auth/phone/oauth-register/', {
            'phone_number': '+8613800138099',
            'code': '123456'
        })
        assert response.status_code == 400

