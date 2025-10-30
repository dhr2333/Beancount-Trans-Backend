import logging
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from project.apps.authentication.models import UserProfile

logger = logging.getLogger(__name__)


class PhoneNumberRequiredBackend(ModelBackend):
    """
    用户名/邮箱+密码认证后端，要求用户必须已绑定手机号
    扩展自ModelBackend，支持用户名和邮箱登录
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        使用用户名或邮箱和密码进行认证
        要求用户必须已绑定手机号
        
        Args:
            request: HTTP 请求对象
            username: 用户名或邮箱
            password: 密码
            
        Returns:
            User 对象或 None
        """
        if username is None:
            username = kwargs.get('email')
        
        if username is None or password is None:
            return None
        
        try:
            # 尝试通过用户名查找用户
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                # 尝试通过邮箱查找用户
                try:
                    user = User.objects.get(email=username)
                except User.DoesNotExist:
                    logger.warning(f"用户名或邮箱 {username} 不存在")
                    return None
                except User.MultipleObjectsReturned:
                    # 如果多个用户有相同邮箱，返回第一个
                    user = User.objects.filter(email=username).first()
            
            # 验证密码
            if user.check_password(password):
                # 检查用户是否已绑定手机号
                try:
                    profile = user.profile
                    if not profile.is_phone_verified():
                        logger.warning(f"用户 {user.username} 尝试登录但未绑定手机号")
                        # 不返回None，允许登录，但中间件会拦截
                        # 这样可以让用户看到需要绑定手机号的提示
                        return user
                    logger.info(f"用户 {user.username} 通过用户名/邮箱密码认证成功")
                    return user
                except UserProfile.DoesNotExist:
                    # 创建UserProfile
                    UserProfile.objects.create(user=user)
                    logger.warning(f"用户 {user.username} 尝试登录但未绑定手机号")
                    return user
            else:
                logger.warning(f"用户名或邮箱 {username} 密码验证失败")
                return None
                
        except Exception as e:
            logger.error(f"用户名/邮箱密码认证异常: {str(e)}")
            return None


class PhonePasswordBackend(ModelBackend):
    """手机号+密码认证后端"""
    
    def authenticate(self, request, phone=None, password=None, **kwargs):
        """
        使用手机号和密码进行认证
        
        Args:
            request: HTTP 请求对象
            phone: 手机号
            password: 密码
            
        Returns:
            User 对象或 None
        """
        if not phone or not password:
            return None
        
        try:
            # 通过手机号查找 UserProfile
            profile = UserProfile.objects.select_related('user').get(phone_number=phone)
            user = profile.user
            
            # 验证密码
            if user.check_password(password):
                logger.info(f"用户 {user.username} 通过手机号密码认证成功")
                return user
            else:
                logger.warning(f"手机号 {phone} 密码验证失败")
                return None
                
        except UserProfile.DoesNotExist:
            logger.warning(f"手机号 {phone} 未绑定任何用户")
            return None
        except Exception as e:
            logger.error(f"手机号密码认证异常: {str(e)}")
            return None


class PhoneCodeBackend(ModelBackend):
    """手机号+验证码认证后端"""
    
    def authenticate(self, request, phone=None, code=None, **kwargs):
        """
        使用手机号和验证码进行认证
        
        Args:
            request: HTTP 请求对象
            phone: 手机号
            code: 验证码
            
        Returns:
            User 对象或 None
        """
        if not phone or not code:
            return None
        
        try:
            # 查找或创建 UserProfile（用于验证码验证）
            # 注意：这里不直接查找用户，因为验证码登录可能用于注册
            profile = UserProfile.objects.select_related('user').filter(phone_number=phone).first()
            
            if not profile:
                # 如果手机号未绑定，创建临时 profile 用于验证码验证
                # 实际的用户创建应该在视图层完成
                temp_profile = UserProfile(phone_number=phone)
            else:
                temp_profile = profile
            
            # 验证验证码
            if temp_profile.verify_sms_code(code, phone):
                if profile:
                    # 手机号已绑定用户，返回用户
                    logger.info(f"用户 {profile.user.username} 通过验证码认证成功")
                    # 标记手机号已验证
                    if not profile.phone_verified:
                        profile.phone_verified = True
                        profile.save()
                    return profile.user
                else:
                    # 手机号未绑定，返回 None（需要在视图层处理注册逻辑）
                    logger.info(f"手机号 {phone} 验证码验证成功，但未绑定用户")
                    return None
            else:
                logger.warning(f"手机号 {phone} 验证码验证失败")
                return None
                
        except Exception as e:
            logger.error(f"手机号验证码认证异常: {str(e)}")
            return None

