from hashlib import sha256

from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie


@ensure_csrf_cookie
def get_csrf_token(request):
    token = get_token(request)
    return JsonResponse({'csrftoken': token})
    # response.set_cookie('csrf_token', token)
    # return response


def get_sha256(str):
    m = sha256(str.encode('utf-8'))
    return m.hexdigest()
