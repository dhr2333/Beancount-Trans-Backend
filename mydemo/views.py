from hashlib import sha256
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from django.shortcuts import redirect
from rest_framework_simplejwt.tokens import RefreshToken
# from dj_rest_auth.registration.views import SocialLoginView
# from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
# from allauth.socialaccount.providers.oauth2.client import OAuth2Client

# class GoogleLogin(SocialLoginView): # if you want to use Authorization Code Grant, use this
#     adapter_class = GoogleOAuth2Adapter
#     callback_url = "http://trans.localhost/api/"
#     client_class = OAuth2Client


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
        # 生成 JWT 令牌
        refresh = RefreshToken.for_user(user)
        access = str(refresh.access_token)
        # 构建响应数据
        data = {
            'access': access,
            'username': user.username
        }
        return JsonResponse(data)
    else:
        # 处理未认证情况
        return JsonResponse({'error': 'User not authenticated'}, status=401)
