# Register your models here.
from django.contrib import admin

from .models import Expense


@admin.register(Expense)
class ExpenseMapAdmin(admin.ModelAdmin):
    list_display = ('key', 'payee', 'payee_order', 'expend', 'tag', 'classification')
    list_per_page = 100
    list_filter = ['payee']
    search_fields = ['key']

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['payee'].required = False
        form.base_fields['payee'].allow_blank = True
        return form
