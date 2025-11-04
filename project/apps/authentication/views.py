import logging
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import get_random_string
from allauth.socialaccount.models import SocialLogin, SocialAccount, SocialToken, SocialApp

from project.apps.authentication.models import UserProfile
from project.apps.authentication.serializers import (
    PhoneSendCodeSerializer,
    PhoneLoginByCodeSerializer,
    PhoneLoginByPasswordSerializer,
    PhoneRegisterSerializer,
    OAuthPhoneRegisterSerializer,
    PhoneBindingSerializer,
    UserBindingsSerializer,
    UserProfileSerializer,
    UserUpdateSerializer,
    TOTPEnableSerializer,
    TOTPDisableSerializer,
    TwoFactorVerifySerializer,
    EmailSendCodeSerializer,
    EmailBindSerializer,
    EmailLoginSendCodeSerializer,
    EmailLoginSerializer,
    UsernameLoginByPasswordSerializer,
)

logger = logging.getLogger(__name__)


class PhoneAuthViewSet(viewsets.GenericViewSet):
    """手机号认证视图集"""
    
    def get_permissions(self):
        """根据不同的 action 设置不同的权限"""
        if self.action in ['send_code', 'login_by_code', 'login_by_password', 'register', 'oauth_context', 'oauth_register']:
            return [AllowAny()]
        return [IsAuthenticated()]

    def _get_sociallogin_from_session(self, request):
        """从 session 中反序列化获取待绑定的社交登录信息"""
        serialized = request.session.get('socialaccount_sociallogin')
        if not serialized:
            return None
        try:
            return SocialLogin.deserialize(serialized)
        except Exception as exc:
            logger.error(f"反序列化社交登录信息失败: {exc}")
            return None

    @staticmethod
    def _clear_sociallogin_in_session(request):
        """清理 session 中缓存的社交登录数据"""
        removed = False
        if 'socialaccount_sociallogin' in request.session:
            del request.session['socialaccount_sociallogin']
            removed = True
        if 'socialaccount_state' in request.session:
            del request.session['socialaccount_state']
            removed = True
        if removed:
            request.session.modified = True

    @staticmethod
    def _generate_available_username(base_username: str) -> str:
        """根据候选值生成唯一用户名"""
        base = (base_username or '').strip()
        if len(base) < 3:
            base = f"user_{base}" if base else 'user'
        base = base[:150]

        candidate = base
        suffix = 1
        while User.objects.filter(username=candidate).exists():
            tail = f"_{suffix}"
            allowed = 150 - len(tail)
            candidate = f"{base[:allowed]}{tail}"
            suffix += 1
        return candidate

    @action(detail=False, methods=['get'], url_path='oauth-context')
    def oauth_context(self, request):
        """获取当前会话中待完成的 OAuth 登录信息"""
        sociallogin = self._get_sociallogin_from_session(request)
        if not sociallogin:
            return Response({'error': '未检测到待处理的社交登录，请重新发起 GitHub 登录'}, status=status.HTTP_404_NOT_FOUND)

        account_extra = sociallogin.account.extra_data or {}
        return Response({
            'provider': sociallogin.account.provider,
            'account': {
                'uid': sociallogin.account.uid,
                'username': sociallogin.user.username or account_extra.get('login') or '',
                'email': sociallogin.user.email or account_extra.get('email') or '',
                'extra_data': account_extra,
            }
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='oauth-register')
    def oauth_register(self, request):
        """处理 GitHub OAuth 首次登录后的手机号注册"""
        sociallogin = self._get_sociallogin_from_session(request)
        if not sociallogin:
            return Response({'error': '未检测到待处理的社交登录，请重新发起 GitHub 登录'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = OAuthPhoneRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone_number = serializer.validated_data['phone_number']
        code = serializer.validated_data['code']
        username_input = serializer.validated_data.get('username', '').strip()
        password = serializer.validated_data.get('password', '')
        email = serializer.validated_data.get('email', '').strip()

        # 验证验证码
        temp_profile = UserProfile(phone_number=phone_number)
        if not temp_profile.verify_sms_code(code, phone_number):
            return Response({'error': '验证码错误或已过期'}, status=status.HTTP_400_BAD_REQUEST)

        account_extra = sociallogin.account.extra_data or {}
        base_username = username_input or sociallogin.user.username or account_extra.get('login') or ''
        username = username_input or self._generate_available_username(base_username)

        if email:
            email = email.strip()
        else:
            email = sociallogin.user.email or account_extra.get('email') or ''

        try:
            with transaction.atomic():
                user = User(username=username, email=email or '')
                if password:
                    user.set_password(password)
                else:
                    user.set_unusable_password()
                user.save()

                profile, _created = UserProfile.objects.get_or_create(user=user)
                profile.phone_number = phone_number
                profile.phone_verified = True
                profile.save()

                # 绑定社交账号
                social_account, created = SocialAccount.objects.get_or_create(
                    provider=sociallogin.account.provider,
                    uid=sociallogin.account.uid,
                    defaults={
                        'user': user,
                        'extra_data': sociallogin.account.extra_data or {}
                    }
                )
                if not created:
                    if social_account.user_id != user.id:
                        raise ValueError('SOCIAL_ACCOUNT_ALREADY_BOUND')
                    social_account.extra_data = sociallogin.account.extra_data or {}
                    social_account.user = user
                    social_account.save()

                if created:
                    social_account.user = user
                    social_account.save(update_fields=['user'])

                # 保存 OAuth token（如果存在）
                token = getattr(sociallogin, 'token', None)
                if token and isinstance(token, SocialToken):
                    try:
                        social_app = SocialApp.objects.filter(provider=sociallogin.account.provider).first()
                        if social_app:
                            token.account = social_account
                            token.app = social_app
                            token.save()
                    except Exception as token_exc:
                        logger.warning(f"保存社交访问令牌失败: {token_exc}")

        except ValueError as exc:
            if str(exc) == 'SOCIAL_ACCOUNT_ALREADY_BOUND':
                logger.warning(f"社交账号 {sociallogin.account.uid} 已被其他用户绑定")
                return Response({'error': '该 GitHub 账号已绑定到其他账户，请改用手机号登录或解绑后重试'}, status=status.HTTP_400_BAD_REQUEST)
            logger.error(f"OAuth 手机号注册失败: {exc}")
            return Response({'error': '注册失败，请稍后重试或使用手机号登录'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as exc:
            logger.error(f"OAuth 手机号注册失败: {exc}")
            return Response({'error': '注册失败，请稍后重试或使用手机号登录'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 清理 session 中的社交登录状态
        self._clear_sociallogin_in_session(request)

        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])

        refresh = RefreshToken.for_user(user)
        logger.info(f"用户 {user.username} 通过 OAuth + 手机号注册成功")

        return Response({
            'message': '注册成功',
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'phone_number': str(phone_number)
            }
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['post'], url_path='send-code')
    def send_code(self, request):
        """发送验证码"""
        serializer = PhoneSendCodeSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        phone_number = serializer.validated_data['phone_number']
        
        try:
            # 创建临时 UserProfile 实例用于发送验证码（不保存到数据库）
            temp_profile = UserProfile(phone_number=phone_number)
            temp_profile.send_sms_code(phone_number)
            
            logger.info(f"验证码发送成功: {phone_number}")
            return Response({
                'message': '验证码已发送',
                'phone_number': str(phone_number)
            }, status=status.HTTP_200_OK)
            
        except ValueError as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"发送验证码失败: {str(e)}")
            return Response({
                'error': '发送验证码失败，请稍后重试'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'], url_path='login-by-code')
    def login_by_code(self, request):
        """验证码登录"""
        serializer = PhoneLoginByCodeSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        phone_number = serializer.validated_data['phone_number']
        code = serializer.validated_data['code']
        
        # 使用验证码认证后端
        user = authenticate(request, phone=str(phone_number), code=code)
        
        if user:
            # 更新最后登录时间
            user.last_login = timezone.now()
            user.save(update_fields=['last_login'])
            
            # 生成 JWT token
            refresh = RefreshToken.for_user(user)
            
            logger.info(f"用户 {user.username} 通过验证码登录成功")
            
            # 检查是否需要2FA验证
            profile = user.profile
            requires_2fa = profile.has_2fa_enabled()
            
            response_data = {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'phone_number': str(phone_number)
                },
                'requires_2fa': requires_2fa
            }
            
            if requires_2fa:
                # 如果启用了2FA，返回需要验证的提示
                response_data['2fa_methods'] = []
                if profile.totp_enabled:
                    response_data['2fa_methods'].append('totp')
            
            return Response(response_data, status=status.HTTP_200_OK)
        else:
            return Response({
                'error': '验证码错误或手机号未注册'
            }, status=status.HTTP_401_UNAUTHORIZED)
    
    @action(detail=False, methods=['post'], url_path='login-by-password')
    def login_by_password(self, request):
        """密码登录（支持TOTP验证）"""
        serializer = PhoneLoginByPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        phone_number = serializer.validated_data['phone_number']
        password = serializer.validated_data['password']
        totp_code = serializer.validated_data.get('totp_code', '').strip()
        
        # 使用密码认证后端
        user = authenticate(request, phone=str(phone_number), password=password)
        
        if user:
            profile = user.profile
            
            # 检查用户是否启用了TOTP
            if profile.totp_enabled:
                if not totp_code:
                    return Response({
                        'error': '该账户已启用TOTP二次验证，请输入TOTP验证码',
                        'requires_totp': True
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # 验证TOTP码
                try:
                    from django_otp.plugins.otp_totp.models import TOTPDevice
                    if profile.totp_device_id:
                        device = TOTPDevice.objects.get(id=profile.totp_device_id, user=user)
                        if not device.verify_token(totp_code):
                            return Response({
                                'error': 'TOTP验证码错误'
                            }, status=status.HTTP_400_BAD_REQUEST)
                    else:
                        return Response({
                            'error': 'TOTP设备不存在，请联系管理员'
                        }, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    logger.error(f"TOTP验证失败: {str(e)}")
                    return Response({
                        'error': 'TOTP验证失败，请稍后重试'
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # 更新最后登录时间
            user.last_login = timezone.now()
            user.save(update_fields=['last_login'])
            
            # 生成 JWT token
            refresh = RefreshToken.for_user(user)
            
            logger.info(f"用户 {user.username} 通过手机号密码登录成功")
            
            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'phone_number': str(phone_number)
                }
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'error': '手机号或密码错误'
            }, status=status.HTTP_401_UNAUTHORIZED)
    
    @action(detail=False, methods=['post'])
    def register(self, request):
        """手机号注册"""
        serializer = PhoneRegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        phone_number = serializer.validated_data['phone_number']
        code = serializer.validated_data['code']
        username = (serializer.validated_data.get('username') or '').strip()
        password = (serializer.validated_data.get('password') or '').strip()
        email = (serializer.validated_data.get('email') or '').strip()
        
        try:
            with transaction.atomic():
                # 验证验证码
                temp_profile = UserProfile(phone_number=phone_number)
                if not temp_profile.verify_sms_code(code, phone_number):
                    return Response({
                        'error': '验证码错误或已过期'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # 若未提供用户名则根据手机号生成一个唯一用户名
                if not username:
                    digits = ''.join(filter(str.isdigit, str(phone_number)))
                    if digits:
                        base_username = f"user_{digits}"
                    else:
                        base_username = f"user_{get_random_string(8)}"

                    candidate = base_username
                    while User.objects.filter(username=candidate).exists():
                        candidate = f"{base_username}_{get_random_string(4)}"
                    username = candidate

                # 创建用户
                user = User.objects.create_user(
                    username=username,
                    password=password or None,
                    email=email or ''
                )
                
                # 更新 UserProfile
                profile = user.profile
                profile.phone_number = phone_number
                profile.phone_verified = True
                profile.save()
                
                # 生成 JWT token
                refresh = RefreshToken.for_user(user)
                
                logger.info(f"用户 {username} 注册成功")
                return Response({
                    'message': '注册成功',
                    'access': str(refresh.access_token),
                    'refresh': str(refresh),
                    'user': {
                        'id': user.id,
                        'username': user.username,
                        'email': user.email,
                        'phone_number': str(phone_number)
                    }
                }, status=status.HTTP_201_CREATED)
                
        except Exception as e:
            logger.error(f"注册失败: {str(e)}")
            return Response({
                'error': f'注册失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UsernameAuthViewSet(viewsets.GenericViewSet):
    """用户名/邮箱+密码认证视图集"""
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=['post'], url_path='login-by-password')
    def login_by_password(self, request):
        """用户名/邮箱+密码登录（支持TOTP验证）"""
        serializer = UsernameLoginByPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        username = serializer.validated_data['username']
        password = serializer.validated_data['password']
        totp_code = serializer.validated_data.get('totp_code', '').strip()
        
        # 使用用户名/邮箱+密码认证后端
        user = authenticate(request, username=username, password=password)
        
        if user:
            try:
                profile = user.profile
            except UserProfile.DoesNotExist:
                profile = UserProfile.objects.create(user=user)
            
            # 检查用户是否启用了TOTP
            if profile.totp_enabled:
                if not totp_code:
                    return Response({
                        'error': '该账户已启用TOTP二次验证，请输入TOTP验证码',
                        'requires_totp': True
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # 验证TOTP码
                try:
                    from django_otp.plugins.otp_totp.models import TOTPDevice
                    if profile.totp_device_id:
                        device = TOTPDevice.objects.get(id=profile.totp_device_id, user=user)
                        if not device.verify_token(totp_code):
                            return Response({
                                'error': 'TOTP验证码错误'
                            }, status=status.HTTP_400_BAD_REQUEST)
                    else:
                        return Response({
                            'error': 'TOTP设备不存在，请联系管理员'
                        }, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    logger.error(f"TOTP验证失败: {str(e)}")
                    return Response({
                        'error': 'TOTP验证失败，请稍后重试'
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # 更新最后登录时间
            user.last_login = timezone.now()
            user.save(update_fields=['last_login'])
            
            # 生成 JWT token
            refresh = RefreshToken.for_user(user)
            
            logger.info(f"用户 {user.username} 通过用户名/邮箱密码登录成功")
            
            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'phone_number': str(profile.phone_number) if profile.phone_number else None
                }
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'error': '用户名/邮箱或密码错误'
            }, status=status.HTTP_401_UNAUTHORIZED)


class EmailAuthViewSet(viewsets.GenericViewSet):
    """邮箱验证码认证视图集"""

    permission_classes = [AllowAny]

    @action(detail=False, methods=['post'], url_path='send-code')
    def send_code(self, request):
        """发送邮箱验证码用于登录"""
        serializer = EmailLoginSendCodeSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data['email']

        try:
            UserProfile.send_email_code(email)
            logger.info(f"邮箱验证码发送成功: {email}")
            return Response({
                'message': '验证码已发送',
                'email': email
            }, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"发送邮箱验证码失败: {email}, {str(e)}")
            return Response({'error': '发送验证码失败，请稍后重试'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path='login-by-code')
    def login_by_code(self, request):
        """邮箱验证码登录"""
        serializer = EmailLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data['email']
        code = serializer.validated_data['code']

        if not UserProfile.verify_email_code(email, code):
            return Response({'error': '验证码错误或已过期'}, status=status.HTTP_401_UNAUTHORIZED)

        user = serializer.get_user()
        if not user:
            return Response({'error': '该邮箱未注册'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            user.last_login = timezone.now()
            user.save(update_fields=['last_login'])

            refresh = RefreshToken.for_user(user)

            logger.info(f"用户 {user.username} 通过邮箱验证码登录成功")

            try:
                profile = user.profile
            except UserProfile.DoesNotExist:
                profile = UserProfile.objects.create(user=user)

            requires_2fa = profile.has_2fa_enabled()

            response_data = {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'phone_number': str(profile.phone_number) if profile.phone_number else None
                },
                'requires_2fa': requires_2fa
            }

            if requires_2fa:
                response_data['2fa_methods'] = []
                if profile.totp_enabled:
                    response_data['2fa_methods'].append('totp')

            return Response(response_data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"邮箱验证码登录失败: {email}, {str(e)}")
            return Response({'error': '登录失败，请稍后重试'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AccountBindingViewSet(viewsets.GenericViewSet):
    """账号绑定管理视图集"""
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """获取当前用户的绑定信息"""
        user = request.user
        profile = user.profile
        
        # 获取社交账号绑定信息
        from allauth.socialaccount.models import SocialAccount
        social_accounts = SocialAccount.objects.filter(user=user)
        
        data = {
            'username': user.username,
            'email': user.email,
            'phone_number': str(profile.phone_number) if profile.phone_number else None,
            'phone_verified': profile.phone_verified,
            'social_accounts': [
                {
                    'provider': account.provider,
                    'uid': account.uid,
                    'extra_data': account.extra_data,
                    'date_joined': account.date_joined
                }
                for account in social_accounts
            ],
            'has_password': user.has_usable_password()
        }
        
        return Response(data, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['post'], url_path='send-email-code')
    def send_email_code(self, request):
        """发送邮箱绑定验证码"""
        serializer = EmailSendCodeSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        email = serializer.validated_data['email']
        try:
            UserProfile.send_email_code(email)
            return Response({'message': '验证码已发送'}, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"发送邮箱验证码失败: {email}, {e}")
            return Response({'error': '发送失败'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path='bind-email')
    def bind_email(self, request):
        """绑定邮箱（需验证码）"""
        serializer = EmailBindSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        email = serializer.validated_data['email']
        code = serializer.validated_data['code']
        if not UserProfile.verify_email_code(email, code):
            return Response({'error': '验证码错误或已过期'}, status=status.HTTP_400_BAD_REQUEST)
        # 设置用户邮箱
        user = request.user
        user.email = email
        user.save(update_fields=['email'])
        logger.info(f"用户 {user.username} 绑定邮箱成功: {email}")
        return Response({'message': '邮箱绑定成功', 'email': email}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['delete'], url_path='unbind-email')
    def unbind_email(self, request):
        """解绑邮箱"""
        user = request.user
        user.email = ''
        user.save(update_fields=['email'])
        logger.info(f"用户 {user.username} 解绑邮箱成功")
        return Response({'message': '邮箱已解绑'}, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['post'], url_path='bind-phone')
    def bind_phone(self, request):
        """绑定手机号"""
        serializer = PhoneBindingSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        phone_number = serializer.validated_data['phone_number']
        code = serializer.validated_data['code']
        
        try:
            # 验证验证码
            temp_profile = UserProfile(phone_number=phone_number)
            if not temp_profile.verify_sms_code(code, phone_number):
                return Response({
                    'error': '验证码错误或已过期'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 更新用户的 profile
            profile = request.user.profile
            profile.phone_number = phone_number
            profile.phone_verified = True
            profile.save()
            
            logger.info(f"用户 {request.user.username} 绑定手机号成功: {phone_number}")
            return Response({
                'message': '手机号绑定成功',
                'phone_number': str(phone_number)
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"绑定手机号失败: {str(e)}")
            return Response({
                'error': f'绑定失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['delete'], url_path='unbind-phone')
    def unbind_phone(self, request):
        """解绑手机号"""
        user = request.user
        profile = user.profile
        
        # 检查是否至少有一种登录方式
        from allauth.socialaccount.models import SocialAccount
        has_social_account = SocialAccount.objects.filter(user=user).exists()
        has_password = user.has_usable_password()
        
        if not has_social_account and not has_password:
            return Response({
                'error': '无法解绑手机号，请至少保留一种登录方式'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not profile.phone_number:
            return Response({
                'error': '您还未绑定手机号'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 解绑手机号
        phone_number = str(profile.phone_number)
        profile.phone_number = None
        profile.phone_verified = False
        profile.save()
        
        logger.info(f"用户 {user.username} 解绑手机号: {phone_number}")
        return Response({
            'message': '手机号解绑成功'
        }, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['delete'], url_path='unbind-social/(?P<provider>[^/.]+)')
    def unbind_social(self, request, provider=None):
        """解绑社交账号"""
        user = request.user
        profile = user.profile
        
        # 检查是否至少有一种登录方式
        from allauth.socialaccount.models import SocialAccount
        social_accounts = SocialAccount.objects.filter(user=user)
        has_phone = bool(profile.phone_number)
        has_password = user.has_usable_password()
        
        if social_accounts.count() == 1 and not has_phone and not has_password:
            return Response({
                'error': '无法解绑社交账号，请至少保留一种登录方式'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 查找要解绑的社交账号
        try:
            social_account = social_accounts.get(provider=provider)
            social_account.delete()
            
            logger.info(f"用户 {user.username} 解绑社交账号: {provider}")
            return Response({
                'message': f'{provider} 账号解绑成功'
            }, status=status.HTTP_200_OK)
            
        except SocialAccount.DoesNotExist:
            return Response({
                'error': f'未找到 {provider} 账号绑定'
            }, status=status.HTTP_404_NOT_FOUND)


class UserProfileViewSet(viewsets.GenericViewSet):
    """用户信息管理视图集"""
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """获取当前用户信息"""
        profile = request.user.profile
        serializer = UserProfileSerializer(profile)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['patch'])
    def update_me(self, request):
        """更新当前用户信息"""
        serializer = UserUpdateSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        user = request.user
        old_username = user.username
        
        # 更新用户名
        if 'username' in serializer.validated_data:
            user.username = serializer.validated_data['username']
            user.save(update_fields=['username'])
            logger.info(f"用户 {old_username} (ID: {user.id}) 更新了用户名: {serializer.validated_data['username']}")
        
        # 更新邮箱
        if 'email' in serializer.validated_data:
            user.email = serializer.validated_data['email']
            user.save(update_fields=['email'])
            logger.info(f"用户 {user.username} 更新了邮箱")
        
        logger.info(f"用户 {user.username} 更新了个人信息")
        
        # 返回更新后的信息
        profile = user.profile
        profile_serializer = UserProfileSerializer(profile)
        return Response(profile_serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='change_password')
    def change_password(self, request):
        """已登录修改密码（仅当前会话用户）"""
        from django.contrib.auth.password_validation import validate_password
        old_password = request.data.get('old_password', '')
        new_password = request.data.get('new_password', '')
        if not old_password or not new_password:
            return Response({'error': '参数不完整'}, status=status.HTTP_400_BAD_REQUEST)
        user = request.user
        if not user.check_password(old_password):
            return Response({'error': '当前密码不正确'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            validate_password(new_password, user)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(new_password)
        user.save(update_fields=['password'])
        logger.info(f"用户 {user.username} 修改密码成功")
        return Response({'message': '密码修改成功'}, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['delete'], url_path='delete_account')
    def delete_account(self, request):
        """删除账户"""
        user = request.user
        
        try:
            from django.db import transaction
            from django.apps import apps
            
            # 删除用户的所有关联数据
            Account = apps.get_model('account_config', 'Account')
            Expense = apps.get_model('maps', 'Expense')
            Assets = apps.get_model('maps', 'Assets')
            Income = apps.get_model('maps', 'Income')
            File = apps.get_model('file_manager', 'File')
            
            # 统计要删除的数据
            account_count = Account.objects.filter(owner=user).count()
            expense_count = Expense.objects.filter(owner=user).count()
            assets_count = Assets.objects.filter(owner=user).count()
            income_count = Income.objects.filter(owner=user).count()
            file_count = File.objects.filter(owner=user).count()
            
            logger.warning(f"用户 {user.username} (ID: {user.id}) 请求删除账户，将删除:")
            logger.warning(f"  账户: {account_count}, 映射: {expense_count + assets_count + income_count}, 文件: {file_count}")
            
            # 使用事务确保数据一致性
            with transaction.atomic():
                # 删除所有关联数据
                Account.objects.filter(owner=user).delete()
                Expense.objects.filter(owner=user).delete()
                Assets.objects.filter(owner=user).delete()
                Income.objects.filter(owner=user).delete()
                File.objects.filter(owner=user).delete()
                
                # 删除社交账号绑定
                from allauth.socialaccount.models import SocialAccount
                SocialAccount.objects.filter(user=user).delete()
                
                # 删除TOTP设备
                try:
                    from django_otp.plugins.otp_totp.models import TOTPDevice
                    TOTPDevice.objects.filter(user=user).delete()
                except Exception:
                    pass  # 如果没有安装django-otp则忽略
                
                # 删除用户profile
                if hasattr(user, 'profile'):
                    user.profile.delete()
                
                # 删除用户
                username = user.username
                user.delete()
            
            logger.info(f"用户 {username} 的账户已删除")
            
            return Response({
                'message': '账户已删除'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"删除账户失败: {str(e)}")
            return Response({
                'error': f'删除账户失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TwoFactorAuthViewSet(viewsets.GenericViewSet):
    """双因素认证视图集"""
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'], url_path='status')
    def status(self, request):
        """获取2FA状态"""
        profile = request.user.profile
        return Response({
            'totp_enabled': profile.totp_enabled,
            'has_2fa': profile.has_2fa_enabled()
        }, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'], url_path='totp/qrcode')
    def totp_qrcode(self, request):
        """生成TOTP二维码"""
        try:
            from django_otp.plugins.otp_totp.models import TOTPDevice
            from django_otp.util import random_hex
            import qrcode
            import io
            import base64
            
            profile = request.user.profile
            
            # 检查是否已启用TOTP
            if profile.totp_enabled and profile.totp_device_id:
                return Response({
                    'error': 'TOTP已启用，请先禁用'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 生成或获取TOTP设备
            device, created = TOTPDevice.objects.get_or_create(
                user=request.user,
                defaults={
                    'name': 'default',
                    'confirmed': False,
                    'key': random_hex(16)  # 16字节=128位，转换为Base32是26个字符
                }
            )
            
            if not created and device.confirmed:
                # 如果设备已确认，重新生成密钥
                device.key = random_hex(16)
                device.confirmed = False
                device.save()
            
            # 生成配置URL
            config_url = device.config_url
            
            # 从config_url中提取并返回 Base32 secret（权威来源）
            # 格式: otpauth://totp/...?secret=XXXXX&...
            import urllib.parse
            parsed_url = urllib.parse.urlparse(config_url)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            secret_key = query_params.get('secret', [''])[0]
            # 去掉可能的填充，保证兼容（KeePass/GA通常都接受去填充形式）
            if secret_key:
                secret_key = secret_key.strip().replace(' ', '')
                if secret_key.endswith('='):
                    secret_key = secret_key.rstrip('=')
            
            # 生成二维码
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(config_url)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            img_str = base64.b64encode(buffer.getvalue()).decode()
            
            # 保存设备ID到profile
            profile.totp_device_id = device.id
            profile.save()
            
            return Response({
                'qr_code': f'data:image/png;base64,{img_str}',
                'secret': secret_key,
                'device_id': device.id
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"生成TOTP二维码失败: {str(e)}")
            return Response({
                'error': f'生成二维码失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'], url_path='totp/enable')
    def totp_enable(self, request):
        """启用TOTP"""
        serializer = TOTPEnableSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        code = serializer.validated_data['code']
        profile = request.user.profile
        
        if not profile.totp_device_id:
            return Response({
                'error': '请先生成TOTP二维码'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            from django_otp.plugins.otp_totp.models import TOTPDevice
            
            device = TOTPDevice.objects.get(id=profile.totp_device_id, user=request.user)
            
            # 验证TOTP码
            if device.verify_token(code):
                # 确认设备
                device.confirmed = True
                device.save()
                
                # 启用TOTP
                profile.totp_enabled = True
                profile.save()
                
                logger.info(f"用户 {request.user.username} 启用TOTP成功")
                return Response({
                    'message': 'TOTP启用成功'
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'error': '验证码错误'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except TOTPDevice.DoesNotExist:
            return Response({
                'error': 'TOTP设备不存在'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"启用TOTP失败: {str(e)}")
            return Response({
                'error': f'启用TOTP失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'], url_path='totp/disable')
    def totp_disable(self, request):
        """禁用TOTP"""
        serializer = TOTPDisableSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        code = serializer.validated_data['code']
        profile = request.user.profile
        
        if not profile.totp_enabled:
            return Response({
                'error': 'TOTP未启用'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            from django_otp.plugins.otp_totp.models import TOTPDevice
            
            device = None
            if profile.totp_device_id:
                device = TOTPDevice.objects.get(id=profile.totp_device_id, user=request.user)
                
                # 验证TOTP码
                if not device.verify_token(code):
                    return Response({
                        'error': '验证码错误'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            # 禁用TOTP
            device_id = profile.totp_device_id
            profile.totp_enabled = False
            profile.totp_device_id = None
            profile.save()
            
            # 删除设备（可选）
            if device_id and device:
                try:
                    device.delete()
                except:
                    pass
            
            logger.info(f"用户 {request.user.username} 禁用TOTP成功")
            return Response({
                'message': 'TOTP禁用成功'
            }, status=status.HTTP_200_OK)
                
        except Exception as e:
            logger.error(f"禁用TOTP失败: {str(e)}")
            return Response({
                'error': f'禁用TOTP失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    
    @action(detail=False, methods=['post'], url_path='verify')
    def verify(self, request):
        """2FA验证（用于登录后验证）"""
        serializer = TwoFactorVerifySerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        code = serializer.validated_data['code']
        method = serializer.validated_data['method']
        profile = request.user.profile
        
        try:
            if method == 'totp':
                if not profile.totp_enabled:
                    return Response({
                        'error': 'TOTP未启用'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                from django_otp.plugins.otp_totp.models import TOTPDevice
                if profile.totp_device_id:
                    device = TOTPDevice.objects.get(id=profile.totp_device_id, user=request.user)
                    if device.verify_token(code):
                        return Response({
                            'message': 'TOTP验证成功'
                        }, status=status.HTTP_200_OK)
                    else:
                        return Response({
                            'error': '验证码错误'
                        }, status=status.HTTP_400_BAD_REQUEST)
                else:
                    return Response({
                        'error': 'TOTP设备不存在'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            else:
                return Response({
                    'error': '不支持的2FA方式'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"2FA验证失败: {str(e)}")
            return Response({
                'error': f'验证失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


