from rest_framework import serializers
from .models import Directory, File

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

    class Meta:
        model = File
        fields = ['id', 'directory', 'owner', 'name', 'size', 'uploaded_at', 'content_type', 'directory_name']

    def get_directory_name(self, obj):
        return obj.directory.name
