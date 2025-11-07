import pytest
from unittest.mock import Mock, MagicMock
from django.contrib.auth.models import User
from django.test import RequestFactory
from allauth.socialaccount.models import SocialAccount, SocialApp
from django.contrib.sites.models import Site
from project.apps.authentication.models import UserProfile
from project.apps.authentication.adapters import CustomSocialAccountAdapter


@pytest.mark.django_db
class TestCustomSocialAccountAdapter:
    """自定义社交账号适配器测试"""
    
    def setup_method(self):
        """设置测试环境"""
        self.factory = RequestFactory()
        self.adapter = CustomSocialAccountAdapter()
    
    def test_is_open_for_signup_returns_true(self):
        """测试允许OAuth自动注册"""
        request = self.factory.get('/')
        sociallogin = Mock()
        
        result = self.adapter.is_open_for_signup(request, sociallogin)
        
        assert result is True
    
    def test_pre_social_login_existing_user_with_phone(self):
        """测试已存在用户且已绑定手机号"""
        user = User.objects.create_user(
            username='testuser',
            password='TestPass123!',
            email='test@example.com'
        )
        user.profile.phone_number = '+8613800138080'
        user.profile.phone_verified = True
        user.profile.save()
        
        request = self.factory.get('/')
        sociallogin = Mock()
        sociallogin.is_existing = True
        sociallogin.user = user
        
        result = self.adapter.pre_social_login(request, sociallogin)
        
        # 应该返回None（允许继续）
        assert result is None
    
    def test_pre_social_login_existing_user_without_phone(self):
        """测试已存在用户但未绑定手机号"""
        user = User.objects.create_user(
            username='testuser2',
            password='TestPass123!',
            email='test2@example.com'
        )
        # 不绑定手机号
        
        request = self.factory.get('/')
        sociallogin = Mock()
        sociallogin.is_existing = True
        sociallogin.user = user
        
        result = self.adapter.pre_social_login(request, sociallogin)
        
        # 应该返回None（允许继续，但中间件会拦截）
        assert result is None
    
    def test_pre_social_login_new_user(self):
        """测试新用户（不允许自动注册）"""
        request = self.factory.get('/')
        sociallogin = Mock()
        sociallogin.is_existing = False
        
        # 由于is_open_for_signup返回False，不会自动创建用户
        # 但pre_social_login仍然会被调用
        result = self.adapter.pre_social_login(request, sociallogin)
        
        # 应该返回None
        assert result is None
    
    def test_save_user_checks_phone(self):
        """测试保存用户时检查手机号"""
        request = self.factory.get('/')
        
        user = User.objects.create_user(
            username='testuser4',
            password='TestPass123!',
            email='test4@example.com'
        )
        
        sociallogin = Mock()
        sociallogin.user = user
        sociallogin.account = Mock()
        sociallogin.account.provider = 'github'
        sociallogin.account.uid = '12345'
        sociallogin.account.extra_data = {}
        
        # Mock父类方法
        from unittest.mock import patch
        with patch.object(
            CustomSocialAccountAdapter.__bases__[0],
            'save_user',
            return_value=user
        ):
            result = self.adapter.save_user(request, sociallogin)
            
            assert result == user
            # 验证profile已创建
            user.refresh_from_db()
            assert hasattr(user, 'profile')
    
    def test_get_connect_redirect_url_with_phone(self):
        """测试已绑定手机号的重定向"""
        from unittest.mock import patch
        
        user = User.objects.create_user(
            username='testuser5',
            password='TestPass123!',
            email='test5@example.com'
        )
        user.profile.phone_number = '+8613800138081'
        user.profile.phone_verified = True
        user.profile.save()
        
        site = Site.objects.get_or_create(domain='example.com', name='example.com')[0]
        app = SocialApp.objects.create(
            provider='github',
            name='GitHub',
            client_id='test_client_id',
            secret='test_secret'
        )
        app.sites.add(site)
        
        social_account = SocialAccount.objects.create(
            user=user,
            provider='github',
            uid='12345',
            extra_data={'login': 'testuser'}
        )
        
        request = self.factory.get('/')
        request.user = user
        
        # Mock父类方法以避免URL反向解析错误
        with patch.object(self.adapter.__class__.__bases__[0], 'get_connect_redirect_url', return_value='/default/redirect/'):
            url = self.adapter.get_connect_redirect_url(request, social_account)
            
            # 已绑定手机号，应该使用父类方法返回的URL
            # 这里我们验证不会返回绑定页面URL
            assert url != '/api/auth/bindings/bind-phone/'
            assert url == '/default/redirect/'
    
    def test_get_connect_redirect_url_without_phone(self):
        """测试未绑定手机号的重定向"""
        user = User.objects.create_user(
            username='testuser6',
            password='TestPass123!',
            email='test6@example.com'
        )
        # 不绑定手机号
        
        site = Site.objects.get_or_create(domain='example.com', name='example.com')[0]
        app = SocialApp.objects.create(
            provider='github',
            name='GitHub',
            client_id='test_client_id',
            secret='test_secret'
        )
        app.sites.add(site)
        
        social_account = SocialAccount.objects.create(
            user=user,
            provider='github',
            uid='12345',
            extra_data={'login': 'testuser'}
        )
        
        request = self.factory.get('/')
        request.user = user
        
        url = self.adapter.get_connect_redirect_url(request, social_account)
        
        # 未绑定手机号，应该返回绑定页面URL
        assert url == '/api/auth/bindings/bind-phone/'

