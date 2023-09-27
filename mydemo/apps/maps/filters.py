from rest_framework import filters


class CurrentUserFilterBackend(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        user = request.user
        if user.is_authenticated:
            owner_id = user.id
        else:
            owner_id = 1  # 若无用户登录，默认使用id=1(管理员)的用户进行查询
        return queryset.filter(owner=owner_id)
        # user = request.user
        # owner_id = user.id if request.user.is_authenticated else 1
        # print(owner_id)
        # return queryset.filter(owner=owner_id)
        # owner_id = request.user.id
        # if user.is_authenticated:
        #     return queryset.filter(owner=owner_id)
        # else:
        #     return queryset.filter(owner=1)  # 若无用户登录，默认使用id=1(管理员)的用户进行查询
