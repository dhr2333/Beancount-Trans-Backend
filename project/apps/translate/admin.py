from django.contrib import admin
from .models import  FormatConfig


@admin.register(FormatConfig)
class FormatConfigMapAdmin(admin.ModelAdmin):
    list_display = ('owner', 'flag', 'show_note', 'show_tag', 'show_uuid', 'show_status', 'show_discount', 'income_template', 'commission_template', 'currency')
    list_per_page = 500
