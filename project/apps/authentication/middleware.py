import logging
from django.http import JsonResponse
from django.urls import resolve
from django.urls.exceptions import Resolver404
from project.apps.authentication.models import UserProfile

logger = logging.getLogger(__name__)


class PhoneNumberRequiredMiddleware:
    """
    手机号绑定检查中间件
    强制所有已认证用户必须绑定手机号才能访问系统
    """
    
    # 排除的URL路径（不需要手机号绑定）
    EXCLUDED_PATHS = [
        '/api/auth/phone/send-code/',
        '/api/auth/phone/login-by-code/',
        '/api/auth/phone/login-by-password/',
        '/api/auth/phone/register/',
        '/api/auth/bindings/bind-phone/',
        '/api/auth/bindings/',  # 绑定相关接口
        # '/api/auth/profile/me/',  # 移除排除，让中间件检查手机号绑定
        '/api/auth/profile/update_me/',
        '/api/auth/token/refresh/',
        '/api/_allauth/',  # allauth相关接口
        '/admin/',
    ]
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # 只检查已认证的用户，匿名用户允许访问（用于访问admin用户数据）
        if request.user.is_authenticated:
            # 检查路径是否在排除列表中
            if not self._is_excluded_path(request.path):
                try:
                    # 检查用户是否已绑定手机号
                    profile = request.user.profile
                    if not profile.is_phone_verified():
                        # 返回需要绑定手机号的响应
                        return JsonResponse({
                            'error': '请先绑定手机号',
                            'code': 'PHONE_NUMBER_REQUIRED',
                            'message': '您需要绑定手机号才能继续使用系统',
                            'redirect_url': '/api/auth/bindings/bind-phone/'
                        }, status=403)
                except AttributeError:
                    # 用户没有profile，创建它（理论上不应该发生，因为信号会自动创建）
                    UserProfile.objects.create(user=request.user)
                    return JsonResponse({
                        'error': '请先绑定手机号',
                        'code': 'PHONE_NUMBER_REQUIRED',
                        'message': '您需要绑定手机号才能继续使用系统',
                        'redirect_url': '/api/auth/bindings/bind-phone/'
                    }, status=403)
                except UserProfile.DoesNotExist:
                    # 用户没有profile，创建它（Django OneToOneField访问不存在对象时抛出此异常）
                    UserProfile.objects.create(user=request.user)
                    return JsonResponse({
                        'error': '请先绑定手机号',
                        'code': 'PHONE_NUMBER_REQUIRED',
                        'message': '您需要绑定手机号才能继续使用系统',
                        'redirect_url': '/api/auth/bindings/bind-phone/'
                    }, status=403)
                except Exception as e:
                    logger.error(f"中间件检查手机号绑定时出错: {str(e)}")
                    # 发生错误时允许继续（避免完全阻断系统）
                    pass
        
        # 匿名用户和已绑定手机号的用户允许继续
        response = self.get_response(request)
        return response
    
    def _is_excluded_path(self, path):
        """检查路径是否在排除列表中"""
        for excluded_path in self.EXCLUDED_PATHS:
            if path.startswith(excluded_path):
                return True
        return False

