from django.contrib import admin

from .models import OwnTrackLog
# Register your models here.

@admin.register(OwnTrackLog)
class OwnTrackLogsAdmin(admin.ModelAdmin):
    ordering=('-tid',)
