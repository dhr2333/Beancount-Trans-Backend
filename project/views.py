from hashlib import sha256
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework_simplejwt.tokens import RefreshToken

@ensure_csrf_cookie
def get_csrf_token(request):
    token = get_token(request)
    JsonResponse({'csrftoken': token}).set_cookie('csrftoken', token)
    return JsonResponse({'csrftoken': token})


def get_sha256(str):
    m = sha256(str.encode('utf-8'))
    return m.hexdigest()


def authenticateByToken(request):
    # 确保用户已通过 Django-allauth 完成 OAuth 流程
    if request.user.is_authenticated:
        user = request.user

        # 判断是否为首次登录（last_login 为 None 表示首次登录）
        is_new_user = user.last_login is None

        # 更新 last_login 时间
        from django.utils import timezone
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])

        # 检查用户是否已绑定手机号
        try:
            profile = user.profile
            phone_verified = profile.is_phone_verified()
        except AttributeError:
            # 用户没有profile，创建它
            from project.apps.authentication.models import UserProfile
            profile = UserProfile.objects.create(user=user)
            phone_verified = False

        # 如果未绑定手机号，返回需要绑定的响应
        if not phone_verified:
            return JsonResponse({
                'error': '请先绑定手机号',
                'code': 'PHONE_NUMBER_REQUIRED',
                'message': '您需要绑定手机号才能继续使用系统',
                'redirect_url': '/api/auth/bindings/bind-phone/',
                'requires_phone_binding': True
            }, status=403)

        # 生成 JWT 令牌
        refresh = RefreshToken.for_user(user)
        access = str(refresh.access_token)

        # 构建响应数据
        data = {
            'access': access,
            'refresh': str(refresh),
            'username': user.username,
            'is_new_user': is_new_user,
            'phone_verified': phone_verified
        }
        return JsonResponse(data)
    else:
        # 处理未认证情况
        return JsonResponse({'error': 'User not authenticated'}, status=401)
