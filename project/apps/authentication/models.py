import random
import logging
from django.db import models
from django.contrib.auth.models import User
from django.core.cache import cache
from django.conf import settings
from phonenumber_field.modelfields import PhoneNumberField
from project.models import BaseModel

logger = logging.getLogger(__name__)


class UserProfile(BaseModel):
    """用户扩展信息模型"""
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='profile',
        verbose_name='用户'
    )
    phone_number = PhoneNumberField(
        unique=True, 
        null=True, 
        blank=True,
        verbose_name='手机号',
        help_text='E164格式的手机号，如+8613800138000'
    )
    phone_verified = models.BooleanField(
        default=False,
        verbose_name='手机号已验证',
        help_text='手机号是否通过验证码验证'
    )
    # 2FA相关字段
    totp_enabled = models.BooleanField(
        default=False,
        verbose_name='启用TOTP双因素认证',
        help_text='是否启用基于时间的一次性密码（TOTP）双因素认证'
    )
    sms_2fa_enabled = models.BooleanField(
        default=False,
        verbose_name='启用SMS双因素认证',
        help_text='是否启用基于短信的双因素认证'
    )
    totp_device_id = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='TOTP设备ID',
        help_text='关联的TOTP设备ID（django-otp）'
    )

    class Meta:
        db_table = 'user_profile'
        verbose_name = '用户扩展信息'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.user.username} - {self.phone_number or '未绑定手机号'}"
    
    def has_2fa_enabled(self):
        """检查是否启用了任何2FA方式"""
        return self.totp_enabled or self.sms_2fa_enabled
    
    def is_phone_verified(self):
        """检查手机号是否已验证"""
        return self.phone_number and self.phone_verified

    @staticmethod
    def generate_sms_code():
        """生成6位数字验证码"""
        return ''.join([str(random.randint(0, 9)) for _ in range(6)])

    def get_sms_cache_key(self, phone_number=None):
        """获取短信验证码的缓存键"""
        phone = phone_number or self.phone_number
        if phone:
            return f"sms:code:{phone}"
        return None

    def get_sms_resend_cache_key(self, phone_number=None):
        """获取短信重发限制的缓存键"""
        phone = phone_number or self.phone_number
        if phone:
            return f"sms:resend:{phone}"
        return None

    def can_send_sms(self, phone_number=None):
        """检查是否可以发送短信（防止频繁发送）"""
        cache_key = self.get_sms_resend_cache_key(phone_number)
        if not cache_key:
            return False
        return not cache.get(cache_key)

    def store_sms_code(self, code, phone_number=None):
        """存储短信验证码到缓存"""
        cache_key = self.get_sms_cache_key(phone_number)
        if not cache_key:
            return False
        
        # 存储验证码，设置过期时间
        expire_seconds = getattr(settings, 'SMS_CODE_EXPIRE_SECONDS', 300)
        cache.set(cache_key, code, expire_seconds)
        
        # 设置重发限制
        resend_interval = getattr(settings, 'SMS_CODE_RESEND_INTERVAL', 60)
        resend_cache_key = self.get_sms_resend_cache_key(phone_number)
        cache.set(resend_cache_key, '1', resend_interval)
        
        logger.info(f"验证码已存储: {cache_key}, 过期时间: {expire_seconds}秒")
        return True

    def verify_sms_code(self, code, phone_number=None):
        """验证短信验证码"""
        cache_key = self.get_sms_cache_key(phone_number)
        if not cache_key:
            return False
        
        stored_code = cache.get(cache_key)
        if not stored_code:
            logger.warning(f"验证码不存在或已过期: {cache_key}")
            return False
        
        if str(stored_code) == str(code):
            # 验证成功，删除缓存的验证码
            cache.delete(cache_key)
            logger.info(f"验证码验证成功: {cache_key}")
            return True
        
        logger.warning(f"验证码不匹配: {cache_key}")
        return False

    def send_sms_code(self, phone_number=None):
        """发送短信验证码"""
        from project.apps.authentication.sms import AliyunSMSService
        
        phone = phone_number or self.phone_number
        if not phone:
            raise ValueError("手机号不能为空")
        
        # 检查是否可以发送
        if not self.can_send_sms(phone):
            resend_interval = getattr(settings, 'SMS_CODE_RESEND_INTERVAL', 60)
            raise ValueError(f"发送过于频繁，请{resend_interval}秒后再试")
        
        # 生成验证码
        code = self.generate_sms_code()
        
        # 存储验证码
        self.store_sms_code(code, phone)
        
        # 发送短信
        sms_service = AliyunSMSService()
        result = sms_service.send_code(str(phone), code)
        
        if not result:
            # 发送失败，清除缓存
            cache_key = self.get_sms_cache_key(phone)
            cache.delete(cache_key)
            raise Exception("短信发送失败")
        
        return True

    # ========== 邮箱验证码（用于邮箱绑定） ==========
    @staticmethod
    def generate_email_code():
        """生成6位数字邮箱验证码"""
        return ''.join([str(random.randint(0, 9)) for _ in range(6)])

    @staticmethod
    def get_email_code_cache_key(email: str) -> str:
        return f"email:code:{email}"

    @staticmethod
    def get_email_resend_cache_key(email: str) -> str:
        return f"email:resend:{email}"

    @staticmethod
    def can_send_email(email: str) -> bool:
        return not cache.get(UserProfile.get_email_resend_cache_key(email))

    @staticmethod
    def store_email_code(email: str, code: str) -> None:
        expire_seconds = getattr(settings, 'EMAIL_CODE_EXPIRE_SECONDS', 300)
        cache.set(UserProfile.get_email_code_cache_key(email), code, expire_seconds)
        resend_interval = getattr(settings, 'EMAIL_CODE_RESEND_INTERVAL', 60)
        cache.set(UserProfile.get_email_resend_cache_key(email), '1', resend_interval)

    @staticmethod
    def verify_email_code(email: str, code: str) -> bool:
        cache_key = UserProfile.get_email_code_cache_key(email)
        stored_code = cache.get(cache_key)
        if not stored_code:
            logger.warning(f"邮箱验证码不存在或已过期: {email}")
            return False
        if str(stored_code) == str(code):
            cache.delete(cache_key)
            return True
        logger.warning(f"邮箱验证码不匹配: {email}")
        return False

    @staticmethod
    def send_email_code(email: str) -> bool:
        from django.core.mail import send_mail
        if not email:
            raise ValueError("邮箱不能为空")
        if not UserProfile.can_send_email(email):
            resend_interval = getattr(settings, 'EMAIL_CODE_RESEND_INTERVAL', 60)
            raise ValueError(f"发送过于频繁，请{resend_interval}秒后再试")
        code = UserProfile.generate_email_code()
        UserProfile.store_email_code(email, code)
        subject = getattr(settings, 'EMAIL_BIND_SUBJECT', '邮箱绑定验证码')
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None)
        message = f"您的验证码是：{code}，{getattr(settings, 'EMAIL_CODE_EXPIRE_SECONDS', 300)}秒内有效。"
        try:
            send_mail(subject, message, from_email, [email], fail_silently=False)
            return True
        except Exception as e:
            cache.delete(UserProfile.get_email_code_cache_key(email))
            logger.error(f"发送邮箱验证码失败: {email}, {e}")
            raise

