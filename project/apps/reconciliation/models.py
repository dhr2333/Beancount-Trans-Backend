"""
对账模块的数据模型

包含周期单位枚举、通用待办任务模型等。
"""
from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

from project.models import BaseModel


class CycleUnit(models.TextChoices):
    """周期单位枚举"""
    DAYS = 'days', '天'
    WEEKS = 'weeks', '周'
    MONTHS = 'months', '月'
    YEARS = 'years', '年'


class ScheduledTask(BaseModel):
    """通用待办模型
    
    支持多种任务类型（对账、AI 反馈确认等），使用 GenericForeignKey 解耦
    """
    TASK_TYPE_CHOICES = [
        ('reconciliation', '对账'),
        ('parse_review', '解析审核'),
        # 后续可扩展其他类型
    ]
    
    STATUS_CHOICES = [
        ('inactive', '未激活'),
        ('pending', '待执行'),
        ('completed', '已完成'),
        ('cancelled', '已取消'),
    ]
    
    task_type = models.CharField(
        max_length=32,
        choices=TASK_TYPE_CHOICES,
        verbose_name="任务类型"
    )
    
    # GenericForeignKey：支持关联到任意模型（Account、其他对象等）
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # scheduled_date：预期执行日期（用户可调整，用于周期计算）
    # 注意：解析待办（parse_review）不需要此字段，但为保持模型一致性，仍需要提供值
    scheduled_date = models.DateField(null=True, blank=True, verbose_name="预期执行日期")
    
    # completed_date：实际完成日期（仅当 status='completed' 时有效）
    completed_date = models.DateField(null=True, blank=True, verbose_name="实际完成日期")
    
    # as_of_date：对账截止日期（仅对 reconciliation 任务有效，用于防止重复对账）
    as_of_date = models.DateField(null=True, blank=True, verbose_name="账本对账日期")
    
    status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="状态"
    )
    
    class Meta:
        db_table = 'scheduled_task'
        verbose_name = '待办任务'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['task_type', 'status', 'scheduled_date']),
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['task_type', 'content_type', 'object_id', 'as_of_date', 'status']),
        ]
        
    def __str__(self):
        return f"{self.get_task_type_display()} - {self.scheduled_date} ({self.get_status_display()})"

    @classmethod
    def get_pending_tasks(cls, task_type=None, as_of_date=None):
        """获取待执行的任务
        
        对于对账任务（reconciliation）：基于 scheduled_date 判断是否到期
        对于解析审核任务（parse_review）：一旦 status='pending' 则直接列出
        """
        from datetime import date
        queryset = cls.objects.filter(status='pending')
        if task_type:
            queryset = queryset.filter(task_type=task_type)
        
        # 解析审核待办不需要 scheduled_date 筛选，直接返回
        if task_type == 'parse_review':
            return queryset
        
        # 对账待办需要基于 scheduled_date 筛选
        if as_of_date is None:
            as_of_date = date.today()
        return queryset.filter(scheduled_date__lte=as_of_date)
