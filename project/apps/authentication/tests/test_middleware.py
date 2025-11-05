import pytest
import json
from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import RequestFactory
from project.apps.authentication.models import UserProfile
from project.apps.authentication.middleware import PhoneNumberRequiredMiddleware


@pytest.mark.django_db
class TestPhoneNumberRequiredMiddleware:
    """手机号绑定检查中间件测试"""
    
    def setup_method(self):
        """设置测试环境"""
        cache.clear()
        self.factory = RequestFactory()
        self.middleware = PhoneNumberRequiredMiddleware(self._get_response)
    
    def _get_response(self, request):
        """模拟响应"""
        from django.http import JsonResponse
        return JsonResponse({'status': 'ok'})
    
    def test_middleware_anonymous_user(self):
        """测试匿名用户允许访问"""
        from django.contrib.auth.models import AnonymousUser
        
        request = self.factory.get('/api/some-endpoint/')
        request.user = AnonymousUser()
        
        response = self.middleware(request)
        
        # 匿名用户应该允许访问
        assert response.status_code == 200
    
    def test_middleware_authenticated_with_phone(self):
        """测试已认证且绑定手机号允许访问"""
        user = User.objects.create_user(
            username='testuser',
            password='TestPass123!',
            email='test@example.com'
        )
        user.profile.phone_number = '+8613800138070'
        user.profile.phone_verified = True
        user.profile.save()
        
        request = self.factory.get('/api/some-endpoint/')
        request.user = user
        
        response = self.middleware(request)
        
        assert response.status_code == 200
    
    def test_middleware_authenticated_without_phone(self):
        """测试已认证但未绑定手机号被拦截"""
        user = User.objects.create_user(
            username='testuser2',
            password='TestPass123!',
            email='test2@example.com'
        )
        # 不绑定手机号
        
        request = self.factory.get('/api/some-endpoint/')
        request.user = user
        
        response = self.middleware(request)
        
        assert response.status_code == 403
        data = json.loads(response.content)
        assert data['code'] == 'PHONE_NUMBER_REQUIRED'
        assert '请先绑定手机号' in data['error']
        assert 'redirect_url' in data
    
    def test_middleware_excluded_paths(self):
        """测试排除路径不受限制"""
        user = User.objects.create_user(
            username='testuser3',
            password='TestPass123!',
            email='test3@example.com'
        )
        # 不绑定手机号
        
        # 测试排除的路径
        excluded_paths = [
            '/api/auth/phone/send-code/',
            '/api/auth/phone/login-by-code/',
            '/api/auth/phone/login-by-password/',
            '/api/auth/phone/register/',
            '/api/auth/bindings/bind-phone/',
            '/api/auth/bindings/',
            '/api/auth/profile/update_me/',
            '/api/auth/token/refresh/',
            '/admin/',
        ]
        
        for path in excluded_paths:
            request = self.factory.get(path)
            request.user = user
            
            response = self.middleware(request)
            
            # 排除路径应该允许访问
            assert response.status_code == 200, f"Path {path} should be excluded"
    
    def test_middleware_excluded_paths_prefix(self):
        """测试排除路径前缀匹配"""
        user = User.objects.create_user(
            username='testuser4',
            password='TestPass123!',
            email='test4@example.com'
        )
        # 不绑定手机号
        
        # 测试前缀匹配
        request = self.factory.get('/api/auth/bindings/list/')
        request.user = user
        
        response = self.middleware(request)
        
        # 应该允许访问（前缀匹配 /api/auth/bindings/）
        assert response.status_code == 200
    
    def test_middleware_error_handling(self):
        """测试异常处理（允许继续避免系统阻断）"""
        user = User.objects.create_user(
            username='testuser6',
            password='TestPass123!',
            email='test6@example.com'
        )
        
        # 创建一个会导致异常的profile访问
        # 通过删除profile但保留关联来模拟异常
        if hasattr(user, 'profile'):
            profile_id = user.profile.id
            UserProfile.objects.filter(id=profile_id).delete()
        
        # Mock一个会导致异常的属性访问
        class MockUser:
            def __init__(self):
                self.is_authenticated = True
            
            @property
            def profile(self):
                raise Exception("Unexpected error")
        
        mock_user = MockUser()
        request = self.factory.get('/api/some-endpoint/')
        request.user = mock_user
        
        # 中间件应该捕获异常并允许继续
        response = self.middleware(request)
        
        # 异常情况下应该允许继续（避免完全阻断系统）
        assert response.status_code == 200

