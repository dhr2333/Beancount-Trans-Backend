from django.conf import settings
from rest_framework import serializers
from .models import GitRepository


def build_webhook_callback_url() -> str:
    return f"https://{settings.BASE_URL}/api/git/webhook/"


class GitRepositorySerializer(serializers.ModelSerializer):
    """Git 仓库序列化器"""

    ssh_clone_url = serializers.ReadOnlyField()
    deploy_key_download_url = serializers.SerializerMethodField()
    webhook_callback_url = serializers.SerializerMethodField()
    setup_instructions = serializers.SerializerMethodField()

    class Meta:
        model = GitRepository
        fields = [
            'id', 'ssh_clone_url', 'repo_name', 'setup_mode', 'provider',
            'remote_ssh_url', 'external_full_name', 'default_branch',
            'deploy_key_public', 'webhook_callback_url', 'setup_instructions',
            'created_with_template',
            'last_sync_at', 'sync_status', 'sync_error',
            'deploy_key_download_url', 'created', 'modified',
        ]
        read_only_fields = [
            'id', 'ssh_clone_url', 'repo_name', 'setup_mode', 'provider',
            'remote_ssh_url', 'external_full_name', 'default_branch',
            'deploy_key_public', 'webhook_callback_url', 'setup_instructions',
            'last_sync_at', 'sync_status', 'sync_error', 'created', 'modified',
        ]

    def get_deploy_key_download_url(self, obj):
        return "/api/git/repository/deploy-key/"

    def get_webhook_callback_url(self, obj):
        if obj.provider == 'gitea_hosted' and not obj.remote_ssh_url:
            return ''
        return build_webhook_callback_url()

    def get_setup_instructions(self, obj):
        if obj.provider == 'gitea_hosted' and not obj.remote_ssh_url:
            return []
        url = build_webhook_callback_url()
        lines = [
            f'在托管平台添加 Webhook，Payload URL：{url}',
            'Content type 选择 application/json；事件勾选 push。',
            'Secret 填入启用时返回的 webhook_secret（仅此一次展示，请保存）。',
            f'仅当推送分支为 {obj.default_branch or "main"} 时触发平台同步。',
        ]
        if obj.provider == 'github':
            lines.insert(0, 'GitHub 账本仓库：Settings → Webhooks → Add webhook')
        elif obj.provider == 'gitlab':
            lines.insert(0, 'GitLab：Settings → Webhooks，Secret token 填 webhook_secret')
        elif obj.provider == 'gitea':
            lines.insert(0, 'Gitea：仓库设置 → Web 钩子，密钥填 webhook_secret')
        return lines


class CreateRepositorySerializer(serializers.Serializer):
    """启用 Git：仅在集成 Gitea 上创建仓库（模板或空库）。已有外部远程请使用 POST .../repository/link/。"""

    template = serializers.BooleanField(
        default=True,
        help_text="是否基于模板创建；False 则为空仓库",
    )


class LinkRepositorySerializer(serializers.Serializer):
    """关联已有远程仓库。"""

    remote_ssh_url = serializers.CharField(required=True, max_length=500)
    provider = serializers.ChoiceField(
        choices=['github', 'gitlab', 'gitea', 'other'],
        default='github',
    )
    default_branch = serializers.CharField(required=False, default='main', max_length=100)
    external_full_name = serializers.CharField(
        required=False, allow_blank=True, default='', max_length=255,
    )


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
    """Gitea/GitHub 等 push Webhook 载荷（宽松校验，具体分支在视图中比对）。"""

    ref = serializers.CharField(required=False, allow_blank=True)
    repository = serializers.DictField(required=False)
    project = serializers.DictField(required=False)
    pusher = serializers.DictField(required=False, allow_null=True)
    commits = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=list,
    )


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
