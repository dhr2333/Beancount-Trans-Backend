from rest_framework.filters import BaseFilterBackend
from django.contrib.auth import get_user_model


class CurrentUserFilterBackend(BaseFilterBackend):
    """统一当前用户过滤器"""

    def filter_queryset(self, request, queryset, view):
        """只返回当前用户的数据"""
        if request.user.is_authenticated:
            return queryset.filter(owner=request.user)
        return queryset.none()


class AnonymousUserFilterBackend(BaseFilterBackend):
    """匿名用户过滤器：未登录用户使用id=1用户的数据"""

    def filter_queryset(self, request, queryset, view):
        """未登录用户返回id=1用户的数据，已登录用户返回自己的数据"""
        if request.user.is_authenticated:
            return queryset.filter(owner=request.user)
        else:
            # 未登录用户使用id=1用户的数据
            User = get_user_model()
            try:
                default_user = User.objects.get(id=1)
                return queryset.filter(owner=default_user)
            except User.DoesNotExist:
                return queryset.none()
