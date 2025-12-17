from django.contrib import admin
from project.apps.authentication.models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone_number', 'phone_verified', 'created', 'modified']
    list_filter = ['phone_verified', 'created']
    search_fields = ['user__username', 'user__email', 'phone_number']
    readonly_fields = ['created', 'modified']

    fieldsets = (
        ('用户信息', {
            'fields': ('user',)
        }),
        ('手机号信息', {
            'fields': ('phone_number', 'phone_verified')
        }),
        ('时间信息', {
            'fields': ('created', 'modified'),
            'classes': ('collapse',)
        }),
    )

