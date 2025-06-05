from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
import uuid

class BillFile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False,help_text="文件唯一标识符")
    owner = models.ForeignKey(User, related_name='billfile',on_delete=models.CASCADE,help_text="文件所有者")
    original_name = models.CharField(max_length=255,help_text="原始文件名")
    storage_path = models.CharField(max_length=1024, unique=True,help_text="minIO存储路径")
    file_size = models.PositiveIntegerField(help_text="文件大小（字节）")
    file_hash = models.CharField(max_length=64,blank=True,help_text="文件内容哈希值，用于去重")
    uploaded_at = models.DateTimeField(default=timezone.now,help_text="上传时间")
    is_active = models.BooleanField(default=True,help_text="是否启用，软删除标志")

    class Meta:
        app_label = 'file_manager'
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['owner', 'uploaded_at'])
        ]
        verbose_name = 'Managed File'

    def __str__(self):
        return f"{self.original_name} ({self.file_size} bytes)"
