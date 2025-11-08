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
    """OAuth回调后将Session用户转换为JWT，并提示手机号绑定状态"""
    if request.user.is_authenticated:
        user = request.user
        previous_last_login = user.last_login

        from django.utils import timezone
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])

        from project.apps.authentication.models import UserProfile
        try:
            profile = user.profile
        except AttributeError:
            profile = UserProfile.objects.create(user=user)
        except UserProfile.DoesNotExist:  # pragma: no cover - 理论上不会触发
            profile = UserProfile.objects.create(user=user)

        phone_verified = profile.is_phone_verified()
        is_new_user = previous_last_login is None

        refresh = RefreshToken.for_user(user)
        access = str(refresh.access_token)

        warnings = []
        phone_binding_required = False
        if not phone_verified:
            phone_binding_required = True
            # warnings.append('请尽快绑定手机号，以便使用短信登录等功能。')
            

        data = {
            'access': access,
            'refresh': str(refresh),
            'username': user.username,
            'is_new_user': is_new_user,
            'phone_verified': phone_verified,
            'phone_binding_required': phone_binding_required,
            'warnings': warnings,
        }

        return JsonResponse(data)

    return JsonResponse({'error': 'User not authenticated'}, status=401)
