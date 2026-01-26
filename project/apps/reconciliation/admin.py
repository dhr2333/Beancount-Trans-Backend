"""
对账模块 Django Admin 配置
"""
from django.contrib import admin
from .models import ScheduledTask


@admin.register(ScheduledTask)
class ScheduledTaskAdmin(admin.ModelAdmin):
    """ScheduledTask 管理界面"""
    list_display = [
        'id', 'task_type', 'get_account_name', 
        'scheduled_date', 'completed_date', 
        'status', 'created'
    ]
    list_filter = ['task_type', 'status', 'scheduled_date']
    search_fields = ['object_id']
    readonly_fields = ['created', 'modified', 'content_type', 'object_id']
    date_hierarchy = 'scheduled_date'
    
    def get_account_name(self, obj):
        """获取关联账户名称"""
        from project.apps.account.models import Account
        if isinstance(obj.content_object, Account):
            return obj.content_object.account
        return f"{obj.content_type} #{obj.object_id}"
    get_account_name.short_description = '关联对象'
