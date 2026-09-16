from django.contrib import admin
from project.apps.authentication.models import PersonalAccessToken, UserProfile


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


@admin.register(PersonalAccessToken)
class PersonalAccessTokenAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'prefix', 'scopes', 'expires_at', 'last_used_at', 'revoked_at', 'created']
    list_filter = ['scopes', 'created', 'revoked_at']
    search_fields = ['name', 'user__username', 'prefix']
    readonly_fields = ['prefix', 'token_hash', 'last_used_at', 'created', 'modified']

