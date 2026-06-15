from django.contrib import admin
from project.apps.tags.models import Tag, TagTemplate, TagTemplateItem


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


@admin.register(TagTemplate)
class TagTemplateAdmin(admin.ModelAdmin):
    """标签模板管理"""
    list_display = ['name', 'is_public', 'is_official', 'owner', 'version', 'items_count']
    list_per_page = 100
    list_filter = ['is_public', 'is_official', 'owner']
    search_fields = ['name', 'description', 'update_notes']
    readonly_fields = ['items_count']

    def items_count(self, obj):
        """显示模板项数量"""
        return obj.items.count()
    items_count.short_description = '标签数量'


@admin.register(TagTemplateItem)
class TagTemplateItemAdmin(admin.ModelAdmin):
    """标签模板项管理"""
    list_display = ['template', 'tag_path', 'enable', 'description']
    list_per_page = 500
    list_filter = ['template', 'enable']
    search_fields = ['tag_path']
