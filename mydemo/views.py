from hashlib import sha256

from django.http import JsonResponse
# from rest_framework.response import Response
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
# from mydemo.utils.token import DRFTokenStrategy

# from rest_framework.views import APIView
# from rest_framework.response import Response
# from rest_framework import status

# class DRFLoginView(APIView):
#     def post(self, request):
#         # 假设用户已经通过 Allauth 认证
#         user = request.user  # 获取当前用户
        
#         token_strategy = DRFTokenStrategy()
#         token = token_strategy.create_access_token(request)
        
#         return Response({'access_token': token}, status=status.HTTP_200_OK)
    
# from allauth.socialaccount.providers.github.views import GitHubOAuth2Adapter
# from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
# from allauth.socialaccount.providers.oauth2.client import OAuth2Client
# from dj_rest_auth.registration.views import SocialLoginView


# class GitHubLogin(SocialLoginView):
#     adapter_class = GitHubOAuth2Adapter
#     callback_url = "http://127.0.0.1:8002/auth/social/github/login/callback/"
#     client_class = OAuth2Client


# class GitHubLogin(SocialLoginView):
#     adapter_class = GitHubOAuth2Adapter

#     def get_response(self):
#         response = super().get_response()
#         response.data['access_token'] = self.request.token  # 添加 access token
#         return response
    
    
    # def post(self, request, *args, **kwargs):
    #     response = super().post(request, *args, **kwargs)
    #     user = self.user
    #     refresh = RefreshToken.for_user(user)
    #     return Response({
    #         'refresh': str(refresh),
    #         'access': str(refresh.access_token),
    #         'username': user.username
    #     })


# class GoogleLogin(SocialLoginView): # if you want to use Authorization Code Grant, use this
#     adapter_class = GoogleOAuth2Adapter
#     callback_url = "http://127.0.0.1:8002/auth/social/google/login/callback/"
#     client_class = OAuth2Client


@ensure_csrf_cookie
def get_csrf_token(request):
    token = get_token(request)
    JsonResponse({'csrftoken': token}).set_cookie('csrftoken', token)
    return JsonResponse({'csrftoken': token})


def get_sha256(str):
    m = sha256(str.encode('utf-8'))
    return m.hexdigest()
