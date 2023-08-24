from rest_framework import filters


class CurrentUserFilterBackend(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        user = request.user
        owner_id = request.user.id
        # print(user, "id = ", owner_id)
        if user.is_authenticated:
            return queryset.filter(owner=owner_id)
        else:
            return queryset.filter(owner=1)  # 若无用户登录，则使用id=1(管理员)的用户进行查询
