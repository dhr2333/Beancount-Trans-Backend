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


class ScheduledTaskUserFilterBackend(BaseFilterBackend):
    """ScheduledTask 用户过滤器：通过关联的 Account 筛选
    
    由于 ScheduledTask 使用 GenericForeignKey 关联 Account，
    无法直接通过 owner 字段过滤，需要通过以下步骤：
    1. 获取用户的所有账户 ID
    2. 筛选 content_type 为 Account 且 object_id 在用户账户列表中的待办
    
    使用场景：
    - ScheduledTaskViewSet 需要根据关联的 Account.owner 过滤待办任务
    """
    
    def filter_queryset(self, request, queryset, view):
        """过滤查询集，只返回当前用户相关的待办"""
        if not request.user.is_authenticated:
            return queryset.none()
        
        from project.apps.account.models import Account
        from django.contrib.contenttypes.models import ContentType
        
        # 获取用户账户ID列表
        user_account_ids = Account.objects.filter(
            owner=request.user
        ).values_list('id', flat=True)
        
        if not user_account_ids:
            # 用户没有账户，返回空查询集
            return queryset.none()
        
        # 筛选 content_type 为 Account 且 object_id 在用户账户列表中的待办
        account_content_type = ContentType.objects.get_for_model(Account)
        return queryset.filter(
            content_type=account_content_type,
            object_id__in=user_account_ids
        )
