import logging
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount import app_settings
from allauth.exceptions import ImmediateHttpResponse
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib.auth import get_user_model
from project.apps.authentication.models import UserProfile

logger = logging.getLogger(__name__)

User = get_user_model()


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """自定义社交账号适配器，禁用自动注册，强制手机号绑定"""
    
    def is_open_for_signup(self, request, sociallogin):
        """
        禁用OAuth自动注册
        所有新用户必须通过手机号验证流程
        """
        return False
    
    def pre_social_login(self, request, sociallogin):
        """
        OAuth登录前的处理
        检查用户是否已绑定手机号
        """
        # 如果用户已经存在（通过email关联）
        if sociallogin.is_existing:
            user = sociallogin.user
            try:
                profile = user.profile
                # 检查是否已绑定手机号
                if not profile.is_phone_verified():
                    logger.warning(f"用户 {user.username} 通过OAuth登录但未绑定手机号")
                    # 这里不抛出异常，让登录继续，但会在后续步骤中检查
                    pass
            except UserProfile.DoesNotExist:
                logger.warning(f"用户 {user.username} 没有UserProfile")
                # 创建UserProfile
                UserProfile.objects.create(user=user)
        
        # 对于新用户，sociallogin.is_existing为False
        # 但由于is_open_for_signup返回False，不会自动创建用户
        # 需要引导用户先绑定手机号
        return None
    
    def save_user(self, request, sociallogin, form=None):
        """
        保存用户时检查手机号绑定
        由于is_open_for_signup返回False，这个方法在新用户时不会被调用
        但为了安全起见，仍然检查
        """
        # 调用父类方法
        user = super().save_user(request, sociallogin, form)
        
        # 确保UserProfile存在
        profile, created = UserProfile.objects.get_or_create(user=user)
        
        # 检查是否已绑定手机号
        if not profile.is_phone_verified():
            logger.warning(f"保存用户 {user.username} 但未绑定手机号")
        
        return user
    
    def get_connect_redirect_url(self, request, socialaccount):
        """
        当用户连接社交账号时的重定向URL
        """
        # 检查是否已绑定手机号
        try:
            profile = request.user.profile
            if not profile.is_phone_verified():
                # 需要先绑定手机号，返回绑定页面URL
                return '/api/auth/bindings/bind-phone/'
        except UserProfile.DoesNotExist:
            UserProfile.objects.create(user=request.user)
            return '/api/auth/bindings/bind-phone/'
        
        return super().get_connect_redirect_url(request, socialaccount)

