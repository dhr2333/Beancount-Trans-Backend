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

from project.apps.authentication.models import UserProfile
from project.apps.authentication.serializers import (
    PhoneSendCodeSerializer,
    PhoneLoginByCodeSerializer,
    PhoneLoginByPasswordSerializer,
    PhoneRegisterSerializer,
    PhoneBindingSerializer,
    UserBindingsSerializer,
    UserProfileSerializer,
    UserUpdateSerializer,
    TOTPEnableSerializer,
    TOTPDisableSerializer,
    SMS2FAEnableSerializer,
    TwoFactorVerifySerializer,
)

logger = logging.getLogger(__name__)


class PhoneAuthViewSet(viewsets.GenericViewSet):
    """手机号认证视图集"""
    
    def get_permissions(self):
        """根据不同的 action 设置不同的权限"""
        if self.action in ['send_code', 'login_by_code', 'login_by_password', 'register']:
            return [AllowAny()]
        return [IsAuthenticated()]
    
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
                if profile.sms_2fa_enabled:
                    response_data['2fa_methods'].append('sms')
            
            return Response(response_data, status=status.HTTP_200_OK)
        else:
            return Response({
                'error': '验证码错误或手机号未注册'
            }, status=status.HTTP_401_UNAUTHORIZED)
    
    @action(detail=False, methods=['post'], url_path='login-by-password')
    def login_by_password(self, request):
        """密码登录"""
        serializer = PhoneLoginByPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        phone_number = serializer.validated_data['phone_number']
        password = serializer.validated_data['password']
        
        # 使用密码认证后端
        user = authenticate(request, phone=str(phone_number), password=password)
        
        if user:
            # 更新最后登录时间
            user.last_login = timezone.now()
            user.save(update_fields=['last_login'])
            
            # 生成 JWT token
            refresh = RefreshToken.for_user(user)
            
            logger.info(f"用户 {user.username} 通过密码登录成功")
            
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
                if profile.sms_2fa_enabled:
                    response_data['2fa_methods'].append('sms')
            
            return Response(response_data, status=status.HTTP_200_OK)
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
        username = serializer.validated_data['username']
        password = serializer.validated_data['password']
        email = serializer.validated_data.get('email', '')
        
        try:
            with transaction.atomic():
                # 验证验证码
                temp_profile = UserProfile(phone_number=phone_number)
                if not temp_profile.verify_sms_code(code, phone_number):
                    return Response({
                        'error': '验证码错误或已过期'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # 创建用户
                user = User.objects.create_user(
                    username=username,
                    password=password,
                    email=email
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
    
    @action(detail=False, methods=['delete'], url_path='delete_account')
    def delete_account(self, request):
        """删除账户"""
        user = request.user
        
        try:
            from django.db import transaction
            from django.apps import apps
            
            # 删除用户的所有关联数据
            Account = apps.get_model('account', 'Account')
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
            'sms_2fa_enabled': profile.sms_2fa_enabled,
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
    
    @action(detail=False, methods=['post'], url_path='sms/enable')
    def sms_2fa_enable(self, request):
        """启用SMS 2FA"""
        serializer = SMS2FAEnableSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        code = serializer.validated_data['code']
        profile = request.user.profile
        
        if not profile.is_phone_verified():
            return Response({
                'error': '请先绑定并验证手机号'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # 验证短信验证码
            if not profile.verify_sms_code(code, profile.phone_number):
                return Response({
                    'error': '验证码错误或已过期'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 启用SMS 2FA
            profile.sms_2fa_enabled = True
            profile.save()
            
            logger.info(f"用户 {request.user.username} 启用SMS 2FA成功")
            return Response({
                'message': 'SMS 2FA启用成功'
            }, status=status.HTTP_200_OK)
                
        except Exception as e:
            logger.error(f"启用SMS 2FA失败: {str(e)}")
            return Response({
                'error': f'启用SMS 2FA失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'], url_path='sms/disable')
    def sms_2fa_disable(self, request):
        """禁用SMS 2FA"""
        profile = request.user.profile
        
        if not profile.sms_2fa_enabled:
            return Response({
                'error': 'SMS 2FA未启用'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # 发送验证码用于确认
            if profile.phone_number:
                profile.send_sms_code(profile.phone_number)
                return Response({
                    'message': '验证码已发送，请使用验证码确认禁用',
                    'requires_code': True
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'error': '未绑定手机号'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"发送禁用确认码失败: {str(e)}")
            return Response({
                'error': f'发送验证码失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'], url_path='sms/disable/confirm')
    def sms_2fa_disable_confirm(self, request):
        """确认禁用SMS 2FA"""
        serializer = SMS2FAEnableSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        code = serializer.validated_data['code']
        profile = request.user.profile
        
        try:
            # 验证短信验证码
            if not profile.verify_sms_code(code, profile.phone_number):
                return Response({
                    'error': '验证码错误或已过期'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 禁用SMS 2FA
            profile.sms_2fa_enabled = False
            profile.save()
            
            logger.info(f"用户 {request.user.username} 禁用SMS 2FA成功")
            return Response({
                'message': 'SMS 2FA禁用成功'
            }, status=status.HTTP_200_OK)
                
        except Exception as e:
            logger.error(f"禁用SMS 2FA失败: {str(e)}")
            return Response({
                'error': f'禁用SMS 2FA失败: {str(e)}'
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
            
            elif method == 'sms':
                if not profile.sms_2fa_enabled:
                    return Response({
                        'error': 'SMS 2FA未启用'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                if not profile.phone_number:
                    return Response({
                        'error': '未绑定手机号'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # 发送验证码并验证
                if profile.verify_sms_code(code, profile.phone_number):
                    return Response({
                        'message': 'SMS验证成功'
                    }, status=status.HTTP_200_OK)
                else:
                    return Response({
                        'error': '验证码错误或已过期'
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


