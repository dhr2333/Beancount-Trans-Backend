import pytest
from django.contrib.auth.models import User, AnonymousUser
from django.test import RequestFactory
from rest_framework.views import APIView
from project.apps.authentication.models import UserProfile
from project.apps.authentication.permissions import (
    PhoneNumberVerifiedPermission,
    PhoneNumberOrReadOnlyPermission
)


@pytest.mark.django_db
class TestPhoneNumberVerifiedPermission:
    """手机号验证权限类测试"""
    
    def setup_method(self):
        """设置测试环境"""
        self.factory = RequestFactory()
        self.permission = PhoneNumberVerifiedPermission()
        self.view = APIView()
    
    def test_has_permission_anonymous(self):
        """测试匿名用户无权限"""
        request = self.factory.get('/api/some-endpoint/')
        request.user = AnonymousUser()
        
        has_permission = self.permission.has_permission(request, self.view)
        
        assert has_permission is False
    
    def test_has_permission_authenticated_with_phone(self):
        """测试已认证且绑定手机号有权限"""
        user = User.objects.create_user(
            username='testuser',
            password='TestPass123!',
            email='test@example.com'
        )
        user.profile.phone_number = '+8613800138090'
        user.profile.phone_verified = True
        user.profile.save()
        
        request = self.factory.get('/api/some-endpoint/')
        request.user = user
        
        has_permission = self.permission.has_permission(request, self.view)
        
        assert has_permission is True
    
    def test_has_permission_authenticated_without_phone(self):
        """测试已认证但未绑定手机号无权限"""
        user = User.objects.create_user(
            username='testuser2',
            password='TestPass123!',
            email='test2@example.com'
        )
        # 不绑定手机号
        
        request = self.factory.get('/api/some-endpoint/')
        request.user = user
        
        has_permission = self.permission.has_permission(request, self.view)
        
        assert has_permission is False
    

@pytest.mark.django_db
class TestPhoneNumberOrReadOnlyPermission:
    """手机号验证权限类（只读操作除外）测试"""
    
    def setup_method(self):
        """设置测试环境"""
        self.factory = RequestFactory()
        self.permission = PhoneNumberOrReadOnlyPermission()
        self.view = APIView()
    
    def test_has_permission_safe_method(self):
        """测试安全方法（GET）允许访问"""
        # 即使是匿名用户也应该允许访问
        request = self.factory.get('/api/some-endpoint/')
        request.user = AnonymousUser()
        
        has_permission = self.permission.has_permission(request, self.view)
        
        assert has_permission is True
    
    def test_has_permission_unsafe_method_with_phone(self):
        """测试非安全方法且绑定手机号有权限"""
        user = User.objects.create_user(
            username='testuser4',
            password='TestPass123!',
            email='test4@example.com'
        )
        user.profile.phone_number = '+8613800138091'
        user.profile.phone_verified = True
        user.profile.save()
        
        request = self.factory.post('/api/some-endpoint/')
        request.user = user
        
        has_permission = self.permission.has_permission(request, self.view)
        
        assert has_permission is True
    
    def test_has_permission_unsafe_method_without_phone(self):
        """测试非安全方法但未绑定手机号无权限"""
        user = User.objects.create_user(
            username='testuser5',
            password='TestPass123!',
            email='test5@example.com'
        )
        # 不绑定手机号
        
        request = self.factory.post('/api/some-endpoint/')
        request.user = user
        
        has_permission = self.permission.has_permission(request, self.view)
        
        assert has_permission is False
    
    def test_has_permission_anonymous_safe_method(self):
        """测试匿名用户访问安全方法"""
        request = self.factory.get('/api/some-endpoint/')
        request.user = AnonymousUser()
        
        has_permission = self.permission.has_permission(request, self.view)
        
        assert has_permission is True

