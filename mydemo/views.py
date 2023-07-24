from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie


@ensure_csrf_cookie
def get_csrf_token(request):
    token = get_token(request)
    response = JsonResponse({'token': token})
    response.set_cookie('csrftoken', token)
    return response
    # response_data = {'csrftoken': token}
    # return JsonResponse(response_data, content_type="application/json,charset=utf-8")
