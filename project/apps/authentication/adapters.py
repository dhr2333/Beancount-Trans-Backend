import logging
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount import app_settings
from allauth.exceptions import ImmediateHttpResponse
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib.auth import get_user_model
from project.apps.authentication.models import UserProfile
from project.apps.authentication.utils import generate_unique_username, validate_username_format

logger = logging.getLogger(__name__)

User = get_user_model()


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """自定义社交账号适配器，允许自动注册并在登录后提示绑定手机号"""

    def is_open_for_signup(self, request, sociallogin):
        """允许OAuth自动注册"""
        return True

    def populate_user(self, request, sociallogin, data):
        """在创建用户之前填充用户数据，处理用户名冲突

        Args:
            request: HTTP 请求对象
            sociallogin: SocialLogin 对象
            data: 从 OAuth 提供商获取的用户数据

        Returns:
            User 对象（未保存到数据库）
        """
        # 调用父类方法获取初始用户数据
        user = super().populate_user(request, sociallogin, data)

        # 检查用户名是否冲突或格式无效
        if user.username:
            original_username = user.username
            # 如果用户名格式无效或已存在，生成新的唯一用户名
            is_valid, _ = validate_username_format(user.username)
            if not is_valid or User.objects.filter(username=user.username).exists():
                logger.info(f"OAuth 用户名 {original_username} 冲突或格式无效，生成新用户名")
                user.username = generate_unique_username(original_username)
                logger.info(f"生成新用户名: {user.username}")

        return user

    def pre_social_login(self, request, sociallogin):
        """OAuth登录前的处理，确保已存在用户具备UserProfile"""
        if sociallogin.is_existing:
            user = sociallogin.user
            try:
                profile = user.profile
                if not profile.is_phone_verified():
                    logger.info("用户 %s 通过OAuth登录，但手机号尚未绑定", user.username)
            except UserProfile.DoesNotExist:
                logger.warning("用户 %s 缺少UserProfile，自动创建", user.username)
                UserProfile.objects.create(user=user)
        return None

    def save_user(self, request, sociallogin, form=None):
        """保存用户时自动创建UserProfile并初始化模板"""
        user = super().save_user(request, sociallogin, form)

        profile, created = UserProfile.objects.get_or_create(user=user)
        if created and profile.phone_verified and not profile.phone_number:
            profile.phone_verified = False
            profile.save(update_fields=["phone_verified"])

        if created:
            try:
                from project.apps.account.signals import apply_official_account_templates
                from project.apps.maps.signals import apply_official_templates

                apply_official_account_templates(user)
                apply_official_templates(user)
            except Exception as exc:  # pragma: no cover - 初始化失败不影响登录
                logger.warning("为用户 %s 应用初始化模板失败: %s", user.username, exc)

        return user

    def get_connect_redirect_url(self, request, socialaccount):
        """当用户连接社交账号时的重定向URL"""
        try:
            profile = request.user.profile
            if not profile.is_phone_verified():
                return '/api/auth/bindings/bind-phone/'
        except UserProfile.DoesNotExist:
            UserProfile.objects.create(user=request.user)
            return '/api/auth/bindings/bind-phone/'

        return super().get_connect_redirect_url(request, socialaccount)

