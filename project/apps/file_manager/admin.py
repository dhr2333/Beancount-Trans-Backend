from django.contrib import admin
from .models import Directory, File

class DirectoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'parent', 'created_at')
    list_filter = ('owner', 'created_at')
    search_fields = ('name', 'owner__username')
    raw_id_fields = ('parent', 'owner')
    readonly_fields = ('created_at',)

    def get_path(self, obj):
        return obj.get_path()
    get_path.short_description = 'Path'

admin.site.register(Directory, DirectoryAdmin)

class FileAdmin(admin.ModelAdmin):
    list_display = ('name', 'directory', 'owner', 'size', 'uploaded_at')
    list_filter = ('directory', 'owner', 'content_type', 'uploaded_at')
    search_fields = ('name', 'owner__username')
    raw_id_fields = ('directory', 'owner')
    readonly_fields = ('uploaded_at', 'storage_name', 'minio_path')

    def minio_path(self, obj):
        return obj.minio_path
    minio_path.short_description = 'MinIO Path'

admin.site.register(File, FileAdmin)