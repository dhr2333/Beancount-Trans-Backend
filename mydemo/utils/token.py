import jwt

import mydemo.settings as settings


# def get_token(request):
#     auth_header = request.headers.get('Authorization')
#     if auth_header:
#         token = auth_header.split(' ')[1]
#         return token
#     else:
#         return None


def get_token(request):
    auth_header = request.headers.get('Authorization')
    if auth_header:
        token_parts = auth_header.split(' ')
        if len(token_parts) == 2:
            return token_parts[1]
    return None


# def decode_token(token):
#     try:
#         payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
#         return payload
#     except jwt.ExpiredSignatureError:
#         return 'Token过期'
#     except jwt.InvalidTokenError:
#         return '无效Token'
    
    
def decode_token(token):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return {'error': 'Token过期'}
    except jwt.InvalidTokenError:
        return {'error': '无效Token'}


# def get_token_user_id(request):
#     token = get_token(request)
#     payload = decode_token(token)
#     if payload != 'Token过期' and payload != '无效Token':
#         return payload['user_id']
#     else:
#         return 1


def get_token_user_id(request):
    token = get_token(request)
    if token:
        payload = decode_token(token)
        if 'error' not in payload:
            return payload.get('user_id', 1)
    return 1