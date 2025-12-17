from rest_framework import serializers
from .models import GitRepository


class GitRepositorySerializer(serializers.ModelSerializer):
    """Git 仓库序列化器"""

    ssh_clone_url = serializers.ReadOnlyField()
    deploy_key_download_url = serializers.SerializerMethodField()

    class Meta:
        model = GitRepository
        fields = [
            'id', 'ssh_clone_url', 'repo_name', 'created_with_template', 
            'last_sync_at', 'sync_status', 'sync_error', 
            'deploy_key_download_url', 'created', 'modified'
        ]
        read_only_fields = [
            'id', 'ssh_clone_url', 'repo_name', 'last_sync_at', 
            'sync_status', 'sync_error', 'created', 'modified'
        ]

    def get_deploy_key_download_url(self, obj):
        """获取 Deploy Key 下载URL"""
        return "/api/git/repository/deploy-key/"


class CreateRepositorySerializer(serializers.Serializer):
    """创建仓库请求序列化器"""

    template = serializers.BooleanField(
        default=True,
        help_text="是否基于模板创建：true=基于模板，false=空仓库"
    )

    def validate_template(self, value):
        """验证模板参数"""
        return value


class SyncStatusSerializer(serializers.Serializer):
    """同步状态序列化器"""

    status = serializers.CharField(help_text="同步状态")
    last_sync_at = serializers.DateTimeField(
        allow_null=True, 
        help_text="最后同步时间"
    )
    error = serializers.CharField(
        allow_null=True, 
        allow_blank=True, 
        help_text="错误信息"
    )


class SyncResponseSerializer(serializers.Serializer):
    """同步响应序列化器"""

    status = serializers.CharField(help_text="同步结果状态")
    message = serializers.CharField(help_text="同步结果消息")
    synced_at = serializers.DateTimeField(
        allow_null=True, 
        help_text="同步完成时间"
    )
    error = serializers.CharField(
        required=False, 
        help_text="错误详情"
    )


class WebhookPayloadSerializer(serializers.Serializer):
    """Gitea Webhook 载荷序列化器"""

    ref = serializers.CharField(help_text="分支引用")
    repository = serializers.DictField(help_text="仓库信息")
    pusher = serializers.DictField(help_text="推送者信息")
    commits = serializers.ListField(
        child=serializers.DictField(), 
        help_text="提交信息"
    )

    def validate_ref(self, value):
        """验证分支引用"""
        if not value.endswith('/main'):
            raise serializers.ValidationError("只处理 main 分支的推送")
        return value


class DeployKeyResponseSerializer(serializers.Serializer):
    """Deploy Key 响应序列化器"""

    filename = serializers.CharField(help_text="文件名")
    content_type = serializers.CharField(help_text="内容类型")
    message = serializers.CharField(help_text="操作消息")
    key_id = serializers.IntegerField(
        required=False, 
        help_text="密钥ID"
    )


class DeleteRepositoryResponseSerializer(serializers.Serializer):
    """删除仓库响应序列化器"""

    message = serializers.CharField(help_text="删除结果消息")
    cleaned_files = serializers.ListField(
        child=serializers.CharField(),
        help_text="已清理的文件列表"
    )

