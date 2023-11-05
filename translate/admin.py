# Register your models here.
from django.contrib import admin

from .models import Expense, Assets


@admin.register(Expense)
class ExpenseMapAdmin(admin.ModelAdmin):
    list_display = ('key', 'payee', 'expend', 'tag', 'classification', 'owner')
    list_per_page = 100
    list_filter = ['owner', 'tag', 'payee']  # 过滤器
    search_fields = ['key']  # 搜索字段

    def get_form(self, request, obj=None, **kwargs):  # 重写get_form方法，设置payee字段非必填
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['payee'].required = False
        form.base_fields['payee'].allow_blank = True
        return form


@admin.register(Assets)
class AssetsMapAdmin(admin.ModelAdmin):
    list_display = ('key', 'full', 'income', 'owner')
    list_per_page = 100
    list_filter = ['owner']
    search_fields = ['full']
