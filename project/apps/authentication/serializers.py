import logging
from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from phonenumber_field.serializerfields import PhoneNumberField
from project.apps.authentication.models import UserProfile

logger = logging.getLogger(__name__)


class PhoneSendCodeSerializer(serializers.Serializer):
    """发送验证码序列化器"""
    phone_number = PhoneNumberField(
        required=True,
        help_text='手机号，格式如 +8613800138000 或 13800138000'
    )

    def validate_phone_number(self, value):
        """验证手机号格式"""
        if not value:
            raise serializers.ValidationError("手机号不能为空")
        return value


class PhoneLoginByCodeSerializer(serializers.Serializer):
    """验证码登录序列化器"""
    phone_number = PhoneNumberField(
        required=True,
        help_text='手机号'
    )
    code = serializers.CharField(
        required=True,
        min_length=6,
        max_length=6,
        help_text='6位数字验证码'
    )

    def validate_code(self, value):
        """验证验证码格式"""
        if not value.isdigit():
            raise serializers.ValidationError("验证码必须是6位数字")
        return value


class PhoneLoginByPasswordSerializer(serializers.Serializer):
    """密码登录序列化器"""
    phone_number = PhoneNumberField(
        required=True,
        help_text='手机号'
    )
    password = serializers.CharField(
        required=True,
        write_only=True,
        help_text='密码'
    )
    totp_code = serializers.CharField(
        required=False,
        allow_blank=True,
        min_length=6,
        max_length=6,
        help_text='TOTP验证码（可选，如果用户启用了TOTP则必填）'
    )
    
    def validate_totp_code(self, value):
        """验证TOTP码格式"""
        if value and not value.isdigit():
            raise serializers.ValidationError("TOTP验证码必须是6位数字")
        return value


class PhoneRegisterSerializer(serializers.Serializer):
    """手机号注册序列化器"""
    phone_number = PhoneNumberField(
        required=True,
        help_text='手机号'
    )
    code = serializers.CharField(
        required=True,
        min_length=6,
        max_length=6,
        help_text='6位数字验证码'
    )
    username = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=150,
        help_text='用户名（可选）'
    )
    password = serializers.CharField(
        required=False,
        allow_blank=True,
        write_only=True,
        help_text='密码（可选）'
    )
    email = serializers.EmailField(
        required=False,
        allow_blank=True,
        help_text='邮箱（可选）'
    )

    def validate_username(self, value):
        """验证用户名是否已存在"""
        value = value.strip()
        if not value:
            return ''
        if len(value) < 3 or len(value) > 150:
            raise serializers.ValidationError("用户名长度为3-150个字符")
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("用户名已存在")
        return value

    def validate_phone_number(self, value):
        """验证手机号是否已被注册"""
        if UserProfile.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("该手机号已被注册")
        return value

    def validate_password(self, value):
        value = value.strip()
        if not value:
            return ''
        validate_password(value)
        return value

    def validate_code(self, value):
        """验证验证码格式"""
        if not value.isdigit():
            raise serializers.ValidationError("验证码必须是6位数字")
        return value


class OAuthPhoneRegisterSerializer(serializers.Serializer):
    """OAuth 首次登录手机号注册序列化器"""
    phone_number = PhoneNumberField(required=True, help_text='手机号')
    code = serializers.CharField(required=True, min_length=6, max_length=6, help_text='6位数字验证码')
    username = serializers.CharField(required=False, allow_blank=True, min_length=3, max_length=150, help_text='用户名（可选）')
    password = serializers.CharField(required=False, allow_blank=True, write_only=True, help_text='密码（可选）')
    email = serializers.EmailField(required=False, allow_blank=True, help_text='邮箱（可选）')

    def validate_phone_number(self, value):
        if UserProfile.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("该手机号已被注册")
        return value

    def validate_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("验证码必须是6位数字")
        return value

    def validate_username(self, value):
        value = value.strip()
        if value and User.objects.filter(username=value).exists():
            raise serializers.ValidationError("用户名已存在")
        return value

    def validate_password(self, value):
        if value:
            validate_password(value)
        return value


class PhoneBindingSerializer(serializers.Serializer):
    """绑定手机号序列化器"""
    phone_number = PhoneNumberField(
        required=True,
        help_text='手机号'
    )
    code = serializers.CharField(
        required=True,
        min_length=6,
        max_length=6,
        help_text='6位数字验证码'
    )

    def validate_phone_number(self, value):
        """验证手机号是否已被其他用户绑定"""
        # 检查是否已被其他用户绑定
        existing_profile = UserProfile.objects.filter(phone_number=value).first()
        if existing_profile:
            # 获取当前用户
            request = self.context.get('request')
            if request and request.user.is_authenticated:
                if existing_profile.user != request.user:
                    raise serializers.ValidationError("该手机号已被其他用户绑定")
        return value

    def validate_code(self, value):
        """验证验证码格式"""
        if not value.isdigit():
            raise serializers.ValidationError("验证码必须是6位数字")
        return value


class SocialAccountSerializer(serializers.Serializer):
    """社交账号序列化器"""
    provider = serializers.CharField(read_only=True, help_text='提供商')
    uid = serializers.CharField(read_only=True, help_text='第三方用户ID')
    extra_data = serializers.JSONField(read_only=True, help_text='额外数据')
    date_joined = serializers.DateTimeField(read_only=True, help_text='绑定时间')


class UserBindingsSerializer(serializers.Serializer):
    """用户绑定信息序列化器"""
    username = serializers.CharField(read_only=True, help_text='用户名')
    email = serializers.EmailField(read_only=True, help_text='邮箱')
    phone_number = PhoneNumberField(read_only=True, help_text='手机号')
    phone_verified = serializers.BooleanField(read_only=True, help_text='手机号是否已验证')
    social_accounts = SocialAccountSerializer(many=True, read_only=True, help_text='已绑定的社交账号')
    has_password = serializers.BooleanField(read_only=True, help_text='是否设置了密码')


class UserProfileSerializer(serializers.ModelSerializer):
    """用户完整信息序列化器"""
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    date_joined = serializers.DateTimeField(source='user.date_joined', read_only=True)
    last_login = serializers.DateTimeField(source='user.last_login', read_only=True)
    
    class Meta:
        model = UserProfile
        fields = [
            'username', 
            'email', 
            'phone_number', 
            'phone_verified',
            'date_joined',
            'last_login',
            'created',
            'modified'
        ]
        read_only_fields = ['phone_verified', 'created', 'modified']


class UserUpdateSerializer(serializers.Serializer):
    """用户信息更新序列化器"""
    username = serializers.CharField(
        required=False,
        min_length=3,
        max_length=150,
        help_text='用户名'
    )
    email = serializers.EmailField(
        required=False,
        help_text='邮箱'
    )
    
    def validate_username(self, value):
        """验证用户名是否已被其他用户使用"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            if User.objects.filter(username=value).exclude(id=request.user.id).exists():
                raise serializers.ValidationError("该用户名已被其他用户使用")
        return value
    
    def validate_email(self, value):
        """验证邮箱是否已被其他用户使用"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            if User.objects.filter(email=value).exclude(id=request.user.id).exists():
                raise serializers.ValidationError("该邮箱已被其他用户使用")
        return value


class TOTPEnableSerializer(serializers.Serializer):
    """启用TOTP序列化器"""
    code = serializers.CharField(
        required=True,
        min_length=6,
        max_length=6,
        help_text='6位TOTP验证码'
    )
    
    def validate_code(self, value):
        """验证验证码格式"""
        if not value.isdigit():
            raise serializers.ValidationError("验证码必须是6位数字")
        return value


class TOTPDisableSerializer(serializers.Serializer):
    """禁用TOTP序列化器"""
    code = serializers.CharField(
        required=True,
        min_length=6,
        max_length=6,
        help_text='6位TOTP验证码（用于确认禁用）'
    )
    
    def validate_code(self, value):
        """验证验证码格式"""
        if not value.isdigit():
            raise serializers.ValidationError("验证码必须是6位数字")
        return value


class SMS2FAEnableSerializer(serializers.Serializer):
    """启用SMS 2FA序列化器"""
    code = serializers.CharField(
        required=True,
        min_length=6,
        max_length=6,
        help_text='6位短信验证码'
    )
    
    def validate_code(self, value):
        """验证验证码格式"""
        if not value.isdigit():
            raise serializers.ValidationError("验证码必须是6位数字")
        return value


class TwoFactorVerifySerializer(serializers.Serializer):
    """2FA验证序列化器"""
    code = serializers.CharField(
        required=True,
        min_length=6,
        max_length=6,
        help_text='6位验证码（TOTP或SMS）'
    )
    method = serializers.ChoiceField(
        choices=['totp', 'sms'],
        required=True,
        help_text='2FA方式：totp或sms'
    )
    
    def validate_code(self, value):
        """验证验证码格式"""
        if not value.isdigit():
            raise serializers.ValidationError("验证码必须是6位数字")
        return value


class OAuthBindSerializer(serializers.Serializer):
    """OAuth绑定序列化器"""
    phone_number = PhoneNumberField(
        required=True,
        help_text='手机号'
    )
    code = serializers.CharField(
        required=True,
        min_length=6,
        max_length=6,
        help_text='6位数字验证码'
    )
    
    def validate_code(self, value):
        """验证验证码格式"""
        if not value.isdigit():
            raise serializers.ValidationError("验证码必须是6位数字")
        return value


# ========== 邮箱绑定相关 ==========
class EmailSendCodeSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

    def validate_email(self, value):
        request = self.context.get('request')
        qs = User.objects.filter(email=value)
        if request and request.user.is_authenticated:
            qs = qs.exclude(id=request.user.id)
        if qs.exists():
            raise serializers.ValidationError('该邮箱已被其他账户使用')
        return value


class EmailBindSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    code = serializers.CharField(required=True, min_length=6, max_length=6)

    def validate_email(self, value):
        request = self.context.get('request')
        qs = User.objects.filter(email=value)
        if request and request.user.is_authenticated:
            qs = qs.exclude(id=request.user.id)
        if qs.exists():
            raise serializers.ValidationError('该邮箱已被其他账户使用')
        return value


class EmailLoginSendCodeSerializer(serializers.Serializer):
    """邮箱验证码登录发送验证码序列化器"""
    email = serializers.EmailField(required=True, help_text='邮箱')

    def validate_email(self, value):
        if not User.objects.filter(email=value, is_active=True).exists():
            raise serializers.ValidationError('该邮箱尚未注册或已被禁用')
        return value


class EmailLoginSerializer(serializers.Serializer):
    """邮箱验证码登录序列化器"""
    email = serializers.EmailField(required=True, help_text='邮箱')
    code = serializers.CharField(required=True, min_length=6, max_length=6, help_text='6位数字验证码')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._user = None

    def validate_email(self, value):
        user = User.objects.filter(email=value, is_active=True).order_by('id').first()
        if not user:
            raise serializers.ValidationError('该邮箱尚未注册或已被禁用')
        self._user = user
        return value

    def validate_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError('验证码必须是6位数字')
        return value

    def get_user(self):
        return self._user


class UsernameLoginByPasswordSerializer(serializers.Serializer):
    """用户名/邮箱+密码登录序列化器"""
    username = serializers.CharField(
        required=True,
        help_text='用户名或邮箱'
    )
    password = serializers.CharField(
        required=True,
        write_only=True,
        help_text='密码'
    )
    totp_code = serializers.CharField(
        required=False,
        allow_blank=True,
        min_length=6,
        max_length=6,
        help_text='TOTP验证码（可选，如果用户启用了TOTP则必填）'
    )
    
    def validate_totp_code(self, value):
        """验证TOTP码格式"""
        if value and not value.isdigit():
            raise serializers.ValidationError("TOTP验证码必须是6位数字")
        return value

