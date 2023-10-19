# Register your models here.
from django.contrib import admin
from . import models

from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

# 自定义User表后，admin界面管理User类
class UserAdmin(DjangoUserAdmin):
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'is_staff', 'mobile', 'groups', 'user_permissions'),
        }),
    )
    # 展示用户呈现的字段
    list_display = ('username', 'mobile', 'is_staff', 'is_active', 'is_superuser')


admin.site.register(models.User, UserAdmin)  # 添加UserAdmin密码展示密文