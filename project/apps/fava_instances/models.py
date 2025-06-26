# Beancount-Trans-Backend/project/apps/fava_instances/models.py
import uuid
from django.db import models
from django.contrib.auth.models import User

class FavaInstance(models.Model):
    STATUS_CHOICES = (
        ('starting', 'Starting'),
        ('running', 'Running'),
        ('stopping', 'Stopping'),
        ('stopped', 'Stopped'),
        ('error', 'Error'),
    )

    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    container_id = models.CharField(max_length=64, blank=True)
    container_name = models.CharField(max_length=128, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='stopped')
    last_accessed = models.DateTimeField(auto_now=True)  # 记录最后访问时间用来生命周期管理
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)  # 用于生成唯一的URL路径

    class Meta:
        db_table = 'fava_instances'  # 自定义数据库表名
        app_label = 'fava_instances'  # 显式声明所属应用
        verbose_name = 'Fava 实例'  # 单数形式的可读名称
        verbose_name_plural = verbose_name  # 复数形式的可读名称
