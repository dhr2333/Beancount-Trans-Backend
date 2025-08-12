# project/apps/file_manager/serializers.py
from rest_framework import serializers
from project.apps.file_manager.models import Directory, File
from project.apps.translate.models import ParseFile

class DirectorySerializer(serializers.ModelSerializer):
    path = serializers.SerializerMethodField()
    owner = serializers.ReadOnlyField(source='owner.username')

    class Meta:
        model = Directory
        fields = ['id', 'owner', 'name', 'parent', 'path', 'created_at']

    def create(self, validated_data):
        validated_data['owner'] = self.context['request'].user
        return super().create(validated_data)

    def get_path(self, obj):
        return obj.get_path()


class FileSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source='owner.username')
    directory_name = serializers.SerializerMethodField()
    parse_status = serializers.SerializerMethodField()
    error_message = serializers.SerializerMethodField()

    class Meta:
        model = File
        fields = ['id', 'directory', 'owner', 'name', 'size', 
                 'uploaded_at', 'content_type', 'directory_name',
                 'parse_status', 'error_message']

    def get_directory_name(self, obj):
        return obj.directory.name

    def get_parse_status(self, obj):
        parse_file = ParseFile.objects.filter(file=obj).first()
        return parse_file.status if parse_file else 'unprocessed'

    def get_error_message(self, obj):
        parse_file = ParseFile.objects.filter(file=obj).first()
        return parse_file.error_message if parse_file and parse_file.status == 'failed' else None
