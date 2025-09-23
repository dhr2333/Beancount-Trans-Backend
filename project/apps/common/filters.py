from rest_framework.filters import BaseFilterBackend


class CurrentUserFilterBackend(BaseFilterBackend):
    """统一当前用户过滤器"""
    
    def filter_queryset(self, request, queryset, view):
        """只返回当前用户的数据"""
        if request.user.is_authenticated:
            return queryset.filter(owner=request.user)
        return queryset.none()
