from rest_framework import serializers
from .models import BillFile
from django.urls import reverse
import humanize  # 用于友好显示文件大小

class BillFileSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()
    file_size_display = serializers.SerializerMethodField()
    owner = serializers.StringRelatedField()  # 显示用户名而非ID

    class Meta:
        model = BillFile
        fields = [
            'id', 'owner', 'original_name', 
            'file_size', 'file_size_display',
            'uploaded_at', 'download_url',
            'is_active'
        ]
        read_only_fields = fields

    def get_download_url(self, obj):
        request = self.context.get('request')
        return request.build_absolute_uri(
            reverse('file-download', kwargs={'pk': obj.id})
        ) if request else None

    def get_file_size_display(self, obj):
        return humanize.naturalsize(obj.file_size)
