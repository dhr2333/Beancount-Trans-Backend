from django.contrib import admin
from project.apps.maps.models import Expense, Assets, Income,Template,TemplateItem


@admin.register(Expense)
class ExpenseMapAdmin(admin.ModelAdmin):
    list_display = ('key', 'payee', 'expend', 'owner','currency')
    list_per_page = 500
    list_filter = ['owner', 'payee']
    search_fields = ['key']

    def get_form(self, request, obj=None, **kwargs):  # 重写get_form方法，设置payee字段非必填
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['payee'].required = False
        form.base_fields['payee'].allow_blank = True
        return form


@admin.register(Assets)
class AssetsMapAdmin(admin.ModelAdmin):
    list_display = ('key', 'full', 'assets', 'owner')
    list_per_page = 500
    list_filter = ['owner']
    search_fields = ['full']


@admin.register(Income)
class IncomeMapAdmin(admin.ModelAdmin):
    list_display = ('key', 'payer', 'income', 'owner')
    list_per_page = 500
    list_filter = ['owner']
    search_fields = ['key']


@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'is_public', 'is_official', 'owner', 'version')
    list_per_page = 100
    list_filter = ['type', 'is_public', 'is_official', 'owner']
    search_fields = ['name', 'description', 'update_notes']


@admin.register(TemplateItem)
class TemplateItemAdmin(admin.ModelAdmin):
    list_display = ('template', 'key', 'account', 'payee', 'payer', 'full', 'currency')
    list_per_page = 500
    list_filter = ['template']
    search_fields = ['key', 'account', 'payee', 'payer', 'full', 'currency']
