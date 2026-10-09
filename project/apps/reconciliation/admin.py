"""
对账模块 Django Admin 配置
"""
from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q

from .models import ScheduledTask, RecurringTask


class ScheduledTaskUserFilter(admin.SimpleListFilter):
    """按用户过滤待办任务（对账：关联账户所有者）"""
    title = '用户'
    parameter_name = 'user'

    def lookups(self, request, model_admin):
        """获取所有在对账待办中出现的用户"""
        from project.apps.account.models import Account

        user_dict = {}

        account_content_type = ContentType.objects.get_for_model(Account)
        account_ids = ScheduledTask.objects.filter(
            content_type=account_content_type
        ).values_list('object_id', flat=True).distinct()
        if account_ids:
            for owner_id, username in Account.objects.filter(
                id__in=account_ids
            ).values_list('owner_id', 'owner__username').distinct():
                user_dict[owner_id] = username

        if not user_dict:
            return []
        users = sorted(user_dict.items(), key=lambda x: x[1])
        return [(str(user_id), username) for user_id, username in users]

    def queryset(self, request, queryset):
        """根据选择的用户过滤查询集"""
        if not self.value():
            return queryset

        from project.apps.account.models import Account

        account_content_type = ContentType.objects.get_for_model(Account)
        user_account_ids = list(
            Account.objects.filter(owner_id=self.value()).values_list('id', flat=True)
        )

        q = Q()
        if user_account_ids:
            q |= Q(content_type=account_content_type, object_id__in=user_account_ids)

        if q:
            return queryset.filter(q)
        return queryset.none()


@admin.register(ScheduledTask)
class ScheduledTaskAdmin(admin.ModelAdmin):
    """ScheduledTask 管理界面"""
    list_display = [
        'id', 'task_type', 'get_account_name', 'get_user',
        'scheduled_date', 'completed_date', 
        'status', 'created', 'as_of_date'
    ]
    list_filter = ['task_type', 'status', 'scheduled_date', ScheduledTaskUserFilter]
    search_fields = ['object_id']
    readonly_fields = ['created', 'modified', 'content_type', 'object_id']
    date_hierarchy = 'scheduled_date'
    
    def get_queryset(self, request):
        """优化查询，预加载 ContentType"""
        queryset = super().get_queryset(request)
        # 预加载 content_type 以减少查询次数
        queryset = queryset.select_related('content_type')
        return queryset

    def get_search_results(self, request, queryset, search_term):
        """支持按 object_id 和关联用户名搜索"""
        base_queryset = queryset
        queryset, may_have_duplicates = super().get_search_results(
            request, queryset, search_term
        )

        search_term = search_term.strip()
        if not search_term:
            return queryset, may_have_duplicates

        from project.apps.account.models import Account

        account_content_type = ContentType.objects.get_for_model(Account)

        user_search_q = Q()
        has_user_match_condition = False

        account_ids = list(
            Account.objects.filter(
                owner__username__icontains=search_term
            ).values_list('id', flat=True)
        )
        if account_ids:
            user_search_q |= Q(
                content_type=account_content_type,
                object_id__in=account_ids,
            )
            has_user_match_condition = True

        if not has_user_match_condition:
            return queryset, may_have_duplicates

        return queryset | base_queryset.filter(user_search_q), True
    
    def get_account_name(self, obj):
        """获取关联对象展示名（对账：账户路径）"""
        from project.apps.account.models import Account

        try:
            co = obj.content_object
            if co is None:
                return f"{obj.content_type} #{obj.object_id}"
            if isinstance(co, Account):
                return co.account
        except (AttributeError, TypeError):
            pass
        return f"{obj.content_type} #{obj.object_id}"
    get_account_name.short_description = '关联对象'

    def get_user(self, obj):
        """获取关联用户（对账：账户所有者）"""
        from project.apps.account.models import Account

        try:
            co = obj.content_object
            if co is None:
                return '-'
            if isinstance(co, Account):
                return co.owner.username
        except (AttributeError, TypeError):
            pass
        return '-'
    get_user.short_description = '用户'


@admin.register(RecurringTask)
class RecurringTaskAdmin(admin.ModelAdmin):
    """RecurringTask 管理界面"""
    list_display = ['id', 'user', 'title', 'rule_text', 'rrule', 'next_date', 'status', 'generated_count']
    list_filter = ['status', 'recurrence_basis']
    search_fields = ['title', 'rule_text']
