from django.contrib import admin
from project.apps.maps.models import Expense, Assets, Income,Template,TemplateItem


@admin.register(Expense)
class ExpenseMapAdmin(admin.ModelAdmin):
    list_display = ('key', 'payee', 'expend', 'owner', 'get_currencies')
    list_per_page = 500
    list_filter = ['owner', 'payee']
    search_fields = ['key']

    def get_currencies(self, obj):
        """显示货币列表"""
        return ', '.join([c.code for c in obj.currencies.all()])
    get_currencies.short_description = '货币'

    def get_form(self, request, obj=None, **kwargs):  # 重写get_form方法，设置payee字段非必填
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['payee'].required = False
        form.base_fields['payee'].allow_blank = True
        return form


@admin.register(Assets)
class AssetsMapAdmin(admin.ModelAdmin):
    list_display = ('key', 'full', 'assets', 'owner', 'get_currencies')
    list_per_page = 500
    list_filter = ['owner']
    search_fields = ['full']
    
    def get_currencies(self, obj):
        """显示货币列表"""
        return ', '.join([c.code for c in obj.currencies.all()])
    get_currencies.short_description = '货币'


@admin.register(Income)
class IncomeMapAdmin(admin.ModelAdmin):
    list_display = ('key', 'payer', 'income', 'owner', 'get_currencies')
    list_per_page = 500
    list_filter = ['owner']
    search_fields = ['key']
    
    def get_currencies(self, obj):
        """显示货币列表"""
        return ', '.join([c.code for c in obj.currencies.all()])
    get_currencies.short_description = '货币'


@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'is_public', 'is_official', 'owner', 'version')
    list_per_page = 100
    list_filter = ['type', 'is_public', 'is_official', 'owner']
    search_fields = ['name', 'description', 'update_notes']


@admin.register(TemplateItem)
class TemplateItemAdmin(admin.ModelAdmin):
    list_display = ('template', 'key', 'account', 'payee', 'payer', 'full', 'get_currencies')
    list_per_page = 500
    list_filter = ['template']
    search_fields = ['key', 'account', 'payee', 'payer', 'full']
    
    def get_currencies(self, obj):
        """显示货币列表"""
        return ', '.join([c.code for c in obj.currencies.all()])
    get_currencies.short_description = '货币'
