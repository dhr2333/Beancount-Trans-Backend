from django.contrib import admin
from .models import GitRepository


@admin.register(GitRepository)
class GitRepositoryAdmin(admin.ModelAdmin):
    list_display = ('owner', 'repo_name', 'created_with_template', 'sync_status', 'last_sync_at', 'created')
    list_filter = ('sync_status', 'created_with_template', 'created')
    search_fields = ('owner__username', 'repo_name')
    readonly_fields = ('created', 'modified', 'gitea_repo_id', 'deploy_key_id')
    
    fieldsets = (
        ('基本信息', {
            'fields': ('owner', 'repo_name', 'repo_url', 'gitea_repo_id', 'created_with_template')
        }),
        ('Deploy Key', {
            'fields': ('deploy_key_id', 'deploy_key_public'),
            'classes': ('collapse',)
        }),
        ('同步状态', {
            'fields': ('sync_status', 'last_sync_at', 'sync_error')
        }),
        ('系统信息', {
            'fields': ('created', 'modified'),
            'classes': ('collapse',)
        })
    )
    
    def has_add_permission(self, request):
        """禁用手动添加，只能通过API创建"""
        return False