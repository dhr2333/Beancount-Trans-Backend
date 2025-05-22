from rest_framework import filters


class CurrentUserFilterBackend(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        owner_id = request.user.id if request.user.is_authenticated else 1  # 若无用户登录，默认使用id=1(管理员)的用户进行查询
        return queryset.filter(owner=owner_id)
