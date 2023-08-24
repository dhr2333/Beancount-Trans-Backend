import jwt

import mydemo.settings as settings


def get_token(request):
    auth_header = request.headers.get('Authorization')
    token = auth_header.split(' ')[1]
    return token


def decode_token(token):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return 'Token过期'
    except jwt.InvalidTokenError:
        return '无效Token'


def get_token_user_id(request):
    token = get_token(request)
    payload = decode_token(token)
    if payload != 'Token过期' and payload != '无效Token':
        return payload['user_id']
    else:
        return 1
