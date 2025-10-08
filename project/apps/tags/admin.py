from django.contrib import admin
from project.apps.tags.models import Tag


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    """标签管理界面"""
    list_display = ['id', 'name', 'get_full_path', 'parent', 'owner', 'enable', 'created', 'modified']
    list_filter = ['enable', 'created', 'owner']
    search_fields = ['name', 'description']
    ordering = ['owner', 'name']
    raw_id_fields = ['owner', 'parent']
    
    fieldsets = (
        ('基础信息', {
            'fields': ('name', 'parent', 'description')
        }),
        ('状态', {
            'fields': ('enable',)
        }),
        ('所属', {
            'fields': ('owner',)
        }),
        ('时间信息', {
            'fields': ('created', 'modified'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created', 'modified']
    
    def get_queryset(self, request):
        """优化查询性能"""
        qs = super().get_queryset(request)
        return qs.select_related('parent', 'owner')
    
    def get_full_path(self, obj):
        """显示完整路径"""
        return obj.get_full_path()
    get_full_path.short_description = '完整路径'
