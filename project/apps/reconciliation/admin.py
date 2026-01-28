"""
对账模块 Django Admin 配置
"""
from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User
from .models import ScheduledTask


class ScheduledTaskUserFilter(admin.SimpleListFilter):
    """按用户过滤待办任务"""
    title = '用户'
    parameter_name = 'user'

    def lookups(self, request, model_admin):
        """获取所有有账户的用户列表"""
        from project.apps.account.models import Account
        
        # 获取所有有账户的用户
        account_content_type = ContentType.objects.get_for_model(Account)
        account_ids = ScheduledTask.objects.filter(
            content_type=account_content_type
        ).values_list('object_id', flat=True).distinct()
        
        if not account_ids:
            return []
        
        # 通过账户ID获取用户信息
        accounts = Account.objects.filter(
            id__in=account_ids
        ).values_list('owner_id', 'owner__username').distinct()
        
        # 构建用户列表，去重并排序
        user_dict = {owner_id: username for owner_id, username in accounts}
        users = sorted(user_dict.items(), key=lambda x: x[1])
        
        return [(user_id, username) for user_id, username in users]

    def queryset(self, request, queryset):
        """根据选择的用户过滤查询集"""
        if self.value():
            from project.apps.account.models import Account
            
            # 获取该用户的所有账户ID
            account_content_type = ContentType.objects.get_for_model(Account)
            user_account_ids = Account.objects.filter(
                owner_id=self.value()
            ).values_list('id', flat=True)
            
            # 筛选关联到这些账户的待办任务
            return queryset.filter(
                content_type=account_content_type,
                object_id__in=user_account_ids
            )
        return queryset


@admin.register(ScheduledTask)
class ScheduledTaskAdmin(admin.ModelAdmin):
    """ScheduledTask 管理界面"""
    list_display = [
        'id', 'task_type', 'get_account_name', 'get_user',
        'scheduled_date', 'completed_date', 
        'status', 'created'
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
    
    def get_account_name(self, obj):
        """获取关联账户名称"""
        from project.apps.account.models import Account
        if isinstance(obj.content_object, Account):
            return obj.content_object.account
        return f"{obj.content_type} #{obj.object_id}"
    get_account_name.short_description = '关联对象'
    
    def get_user(self, obj):
        """获取关联用户"""
        from project.apps.account.models import Account
        try:
            if isinstance(obj.content_object, Account):
                return obj.content_object.owner.username
        except (AttributeError, TypeError):
            # 如果 content_object 不存在或无法访问 owner，返回 '-'
            pass
        return '-'
    get_user.short_description = '用户'
