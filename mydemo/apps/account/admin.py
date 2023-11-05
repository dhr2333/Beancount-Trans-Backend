from django.contrib import admin

from .models import Account


# Register your models here.


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('date', 'status', 'account', 'currency', 'note', 'account_type', 'owner')
    list_per_page = 100
    list_filter = ['account_type']
    search_fields = ['date']
