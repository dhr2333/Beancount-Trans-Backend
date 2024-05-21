import jwt

import mydemo.settings as settings


def get_token(request):
    auth_header = request.headers.get('Authorization')
    if auth_header:
        token_parts = auth_header.split(' ')
        if len(token_parts) == 2:
            return token_parts[1]
    return None


def decode_token(token):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
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