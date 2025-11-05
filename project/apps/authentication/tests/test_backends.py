import pytest
from django.contrib.auth.models import User
from django.core.cache import cache
from project.apps.authentication.models import UserProfile
from project.apps.authentication.backends import (
    PhoneNumberRequiredBackend,
    PhonePasswordBackend,
    PhoneCodeBackend
)


@pytest.mark.django_db
class TestPhoneNumberRequiredBackend:
    """用户名/邮箱+密码认证后端测试"""
    
    def setup_method(self):
        """设置测试环境"""
        cache.clear()
        self.backend = PhoneNumberRequiredBackend()
    
    def test_authenticate_by_username_success(self):
        """测试用户名认证成功"""
        user = User.objects.create_user(
            username='testuser',
            password='TestPass123!',
            email='test@example.com'
        )
        user.profile.phone_number = '+8613800138050'
        user.profile.phone_verified = True
        user.profile.save()
        
        authenticated_user = self.backend.authenticate(
            None,
            username='testuser',
            password='TestPass123!'
        )
        
        assert authenticated_user == user
    
    def test_authenticate_by_email_success(self):
        """测试邮箱认证成功"""
        user = User.objects.create_user(
            username='testuser2',
            password='TestPass123!',
            email='test2@example.com'
        )
        user.profile.phone_number = '+8613800138051'
        user.profile.phone_verified = True
        user.profile.save()
        
        authenticated_user = self.backend.authenticate(
            None,
            username='test2@example.com',
            password='TestPass123!'
        )
        
        assert authenticated_user == user
    
    def test_authenticate_by_email_multiple_users(self):
        """测试多个用户相同邮箱"""
        user1 = User.objects.create_user(
            username='testuser3',
            password='TestPass123!',
            email='shared@example.com'
        )
        user1.profile.phone_number = '+8613800138052'
        user1.profile.phone_verified = True
        user1.profile.save()
        
        user2 = User.objects.create_user(
            username='testuser4',
            password='TestPass123!',
            email='shared@example.com'
        )
        user2.profile.phone_number = '+8613800138053'
        user2.profile.phone_verified = True
        user2.profile.save()
        
        authenticated_user = self.backend.authenticate(
            None,
            username='shared@example.com',
            password='TestPass123!'
        )
        
        # 应该返回第一个匹配的用户
        assert authenticated_user in [user1, user2]
    
    def test_authenticate_wrong_password(self):
        """测试密码错误"""
        user = User.objects.create_user(
            username='testuser5',
            password='TestPass123!',
            email='test5@example.com'
        )
        user.profile.phone_number = '+8613800138054'
        user.profile.phone_verified = True
        user.profile.save()
        
        authenticated_user = self.backend.authenticate(
            None,
            username='testuser5',
            password='WrongPassword'
        )
        
        assert authenticated_user is None
    
    def test_authenticate_user_not_found(self):
        """测试用户不存在"""
        authenticated_user = self.backend.authenticate(
            None,
            username='nonexistent',
            password='TestPass123!'
        )
        
        assert authenticated_user is None
    
    def test_authenticate_without_phone(self):
        """测试未绑定手机号（允许登录但中间件会拦截）"""
        user = User.objects.create_user(
            username='testuser6',
            password='TestPass123!',
            email='test6@example.com'
        )
        # 不绑定手机号
        
        authenticated_user = self.backend.authenticate(
            None,
            username='testuser6',
            password='TestPass123!'
        )
        
        # 应该返回用户（中间件会拦截）
        assert authenticated_user == user
    
    def test_authenticate_without_profile(self):
        """测试用户没有Profile（自动创建）"""
        user = User.objects.create_user(
            username='testuser7',
            password='TestPass123!',
            email='test7@example.com'
        )
        # 删除profile
        if hasattr(user, 'profile'):
            user.profile.delete()
        
        authenticated_user = self.backend.authenticate(
            None,
            username='testuser7',
            password='TestPass123!'
        )
        
        # 应该返回用户并创建profile
        assert authenticated_user == user
        user.refresh_from_db()
        assert hasattr(user, 'profile')


@pytest.mark.django_db
class TestPhonePasswordBackend:
    """手机号+密码认证后端测试"""
    
    def setup_method(self):
        """设置测试环境"""
        cache.clear()
        self.backend = PhonePasswordBackend()
    
    def test_authenticate_success(self):
        """测试认证成功"""
        user = User.objects.create_user(
            username='testuser8',
            password='TestPass123!',
            email='test8@example.com'
        )
        user.profile.phone_number = '+8613800138055'
        user.profile.save()
        
        authenticated_user = self.backend.authenticate(
            None,
            phone='+8613800138055',
            password='TestPass123!'
        )
        
        assert authenticated_user == user
    
    def test_authenticate_wrong_password(self):
        """测试密码错误"""
        user = User.objects.create_user(
            username='testuser9',
            password='TestPass123!',
            email='test9@example.com'
        )
        user.profile.phone_number = '+8613800138056'
        user.profile.save()
        
        authenticated_user = self.backend.authenticate(
            None,
            phone='+8613800138056',
            password='WrongPassword'
        )
        
        assert authenticated_user is None
    
    def test_authenticate_phone_not_bound(self):
        """测试手机号未绑定"""
        authenticated_user = self.backend.authenticate(
            None,
            phone='+8613800138057',
            password='TestPass123!'
        )
        
        assert authenticated_user is None
    
    def test_authenticate_missing_phone(self):
        """测试缺少手机号"""
        authenticated_user = self.backend.authenticate(
            None,
            password='TestPass123!'
        )
        
        assert authenticated_user is None
    
    def test_authenticate_missing_password(self):
        """测试缺少密码"""
        authenticated_user = self.backend.authenticate(
            None,
            phone='+8613800138058'
        )
        
        assert authenticated_user is None


@pytest.mark.django_db
class TestPhoneCodeBackend:
    """手机号+验证码认证后端测试"""
    
    def setup_method(self):
        """设置测试环境"""
        cache.clear()
        self.backend = PhoneCodeBackend()
    
    def test_authenticate_success(self):
        """测试认证成功（手机号已绑定）"""
        user = User.objects.create_user(
            username='testuser10',
            password='TestPass123!',
            email='test10@example.com'
        )
        user.profile.phone_number = '+8613800138059'
        user.profile.phone_verified = False  # 验证后会设置为True
        user.profile.save()
        
        # 存储验证码
        user.profile.store_sms_code('123456', user.profile.phone_number)
        
        authenticated_user = self.backend.authenticate(
            None,
            phone='+8613800138059',
            code='123456'
        )
        
        assert authenticated_user == user
        # 验证phone_verified已设置
        user.profile.refresh_from_db()
        assert user.profile.phone_verified is True
    
    def test_authenticate_code_verified_unbound(self):
        """测试验证码正确但手机号未绑定（返回None）"""
        phone_number = '+8613800138060'
        
        # 存储验证码（但不绑定用户）
        temp_profile = UserProfile(phone_number=phone_number)
        temp_profile.store_sms_code('123456', phone_number)
        
        authenticated_user = self.backend.authenticate(
            None,
            phone=phone_number,
            code='123456'
        )
        
        # 应该返回None（需要在视图层处理注册）
        assert authenticated_user is None
    
    def test_authenticate_wrong_code(self):
        """测试验证码错误"""
        user = User.objects.create_user(
            username='testuser11',
            password='TestPass123!',
            email='test11@example.com'
        )
        user.profile.phone_number = '+8613800138061'
        user.profile.save()
        
        user.profile.store_sms_code('123456', user.profile.phone_number)
        
        authenticated_user = self.backend.authenticate(
            None,
            phone='+8613800138061',
            code='654321'  # 错误验证码
        )
        
        assert authenticated_user is None
    
    def test_authenticate_expired_code(self):
        """测试验证码过期"""
        user = User.objects.create_user(
            username='testuser12',
            password='TestPass123!',
            email='test12@example.com'
        )
        user.profile.phone_number = '+8613800138062'
        user.profile.save()
        
        # 存储验证码然后删除（模拟过期）
        user.profile.store_sms_code('123456', user.profile.phone_number)
        cache_key = user.profile.get_sms_cache_key(user.profile.phone_number)
        cache.delete(cache_key)
        
        authenticated_user = self.backend.authenticate(
            None,
            phone='+8613800138062',
            code='123456'
        )
        
        assert authenticated_user is None
    
    def test_authenticate_missing_phone(self):
        """测试缺少手机号"""
        authenticated_user = self.backend.authenticate(
            None,
            code='123456'
        )
        
        assert authenticated_user is None
    
    def test_authenticate_missing_code(self):
        """测试缺少验证码"""
        authenticated_user = self.backend.authenticate(
            None,
            phone='+8613800138063'
        )
        
        assert authenticated_user is None
    
    def test_authenticate_phone_verified_flag(self):
        """测试验证后自动设置phone_verified标志"""
        user = User.objects.create_user(
            username='testuser13',
            password='TestPass123!',
            email='test13@example.com'
        )
        user.profile.phone_number = '+8613800138064'
        user.profile.phone_verified = False
        user.profile.save()
        
        user.profile.store_sms_code('123456', user.profile.phone_number)
        
        authenticated_user = self.backend.authenticate(
            None,
            phone='+8613800138064',
            code='123456'
        )
        
        assert authenticated_user == user
        user.profile.refresh_from_db()
        assert user.profile.phone_verified is True

