import os 
import jwt
import typing
from django.http import HttpRequest
from allauth.headless.tokens.base import AbstractTokenStrategy
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
from django.contrib.sessions.backends.base import SessionBase
from allauth.headless.internal import sessionkit

settings_module = os.environ.get('DJANGO_SETTINGS_MODULE')
if settings_module == 'conf.prod':
    from conf.prod import *
elif settings_module == 'conf.develop':
    from conf.develop import *
else:
    from mydemo.settings import *

class JWTTokenStrategy(AbstractTokenStrategy):
    def create_access_token(self, request: HttpRequest) -> str:
        # 生成访问令牌
        access_token = AccessToken.for_user(request.user)
        return str(access_token)

    def create_refresh_token(self, request: HttpRequest) -> str:
        # 生成刷新令牌
        refresh_token = RefreshToken.for_user(request.user)
        return str(refresh_token)

    def create_access_token_payload(self, request: HttpRequest) -> typing.Optional[dict]:
        # 创建访问令牌的负载
        access_token = self.create_access_token(request)
        # refresh_token = self.create_refresh_token(request)

        return {
            'access_token': access_token,
            # 'refresh_token': refresh_token,
            # 'token_type': 'Bearer',
            # 'expires_in': AccessToken.LIFETIME.total_seconds(),
        }

    def create_session_token(self, request: HttpRequest) -> str:
        if not request.session.session_key:
            request.session.save()
        key = request.session.session_key
        assert isinstance(key, str)  # We did save.
        return key
        # return request.session.session_key if request.session.session_key else ''

    def lookup_session(self, session_token: str) -> typing.Optional[SessionBase]:
        session_key = session_token
        if sessionkit.session_store().exists(session_key):
            return sessionkit.session_store(session_key)
        return None


def get_token(request):
    auth_header = request.headers.get('Authorization')
    if auth_header:
        token_parts = auth_header.split(' ')
        if len(token_parts) == 2:
            return token_parts[1]
    return None


def decode_token(token):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return {'error': 'Token过期'}
    except jwt.InvalidTokenError:
        return {'error': '无效Token'}


def get_token_user_id(request):
    token = get_token(request)
    if token:
        payload = decode_token(token)
        if 'error' not in payload:
            return payload.get('user_id', 1)
    return 1