from django.contrib import admin
from project.apps.owntracks.models import OwnTrackLog
# Register your models here.

@admin.register(OwnTrackLog)
class OwnTrackLogsAdmin(admin.ModelAdmin):
    ordering=('-tid',)
