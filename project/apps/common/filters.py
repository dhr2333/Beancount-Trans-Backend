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
    """ScheduledTask 用户过滤器：通过关联的 Account、ParseFile 或 User 筛选
    
    由于 ScheduledTask 使用 GenericForeignKey 关联不同的模型，
    无法直接通过 owner 字段过滤，需要根据 content_type 分别处理：
    1. Account 类型：通过 Account.owner 过滤
    2. ParseFile 类型：通过 ParseFile.file.owner 过滤
    3. User 类型：通过 object_id == 当前用户 ID 过滤（用户级统一审核待办）
    
    使用场景：
    - ScheduledTaskViewSet 需要根据关联对象的 owner 过滤待办任务
    """
    
    def filter_queryset(self, request, queryset, view):
        """过滤查询集，只返回当前用户相关的待办"""
        if not request.user.is_authenticated:
            return queryset.none()
        
        from project.apps.account.models import Account
        from django.contrib.contenttypes.models import ContentType
        from django.db.models import Q
        
        # 获取 Account 类型的 ContentType
        account_content_type = ContentType.objects.get_for_model(Account)
        
        # 获取 User 类型的 ContentType（用户级统一审核待办）
        user_content_type = ContentType.objects.get_for_model(get_user_model())
        
        # 获取用户账户ID列表
        user_account_ids = list(Account.objects.filter(
            owner=request.user
        ).values_list('id', flat=True))
        
        # 获取 ParseFile 类型的 ContentType 和用户相关的 ParseFile ID
        try:
            from project.apps.translate.models import ParseFile
            parse_file_content_type = ContentType.objects.get_for_model(ParseFile)
            
            # 获取用户的所有 File ID
            from project.apps.file_manager.models import File
            user_file_ids = list(File.objects.filter(
                owner=request.user
            ).values_list('id', flat=True))
            
            # 获取这些 File 对应的 ParseFile ID（ParseFile 的主键就是 file_id）
            user_parse_file_ids = list(ParseFile.objects.filter(
                file_id__in=user_file_ids
            ).values_list('file_id', flat=True))
            
            # 构建查询条件：Account 类型 OR ParseFile 类型 OR User 类型
            conditions = Q(
                content_type=user_content_type,
                object_id=request.user.id
            )
            
            if user_account_ids:
                conditions |= Q(
                    content_type=account_content_type,
                    object_id__in=user_account_ids
                )
            
            if user_parse_file_ids:
                conditions |= Q(
                    content_type=parse_file_content_type,
                    object_id__in=user_parse_file_ids
                )
            
            return queryset.filter(conditions)
            
        except Exception as e:
            # 如果 ParseFile 导入失败，回退到 Account + User
            conditions = Q(
                content_type=user_content_type,
                object_id=request.user.id
            )
            if user_account_ids:
                conditions |= Q(
                    content_type=account_content_type,
                    object_id__in=user_account_ids
                )
            return queryset.filter(conditions)
