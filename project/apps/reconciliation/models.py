"""
对账模块的数据模型

包含周期单位枚举、通用待办任务模型等。
"""
from django.db import models
from django.contrib.auth.models import User
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
        ('entry_review', '条目审核'),
        ('recurring', '循环待办'),
        # 后续可扩展其他类型
    ]
    
    STATUS_CHOICES = [
        ('inactive', '未激活'),
        ('pending', '待执行'),
        ('completed', '已完成'),
        ('cancelled', '已取消'),
        ('revoked', '已撤销'),
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
    # 注意：条目审核待办（entry_review）不需要此字段，但为保持模型一致性，仍需要提供值
    scheduled_date = models.DateField(null=True, blank=True, verbose_name="预期执行日期")
    
    # completed_date：实际完成日期（仅当 status='completed' 时有效）
    completed_date = models.DateField(null=True, blank=True, verbose_name="实际完成日期")
    
    # as_of_date：对账截止日期（仅对 reconciliation 任务有效，用于防止重复对账）
    as_of_date = models.DateField(null=True, blank=True, verbose_name="账本对账日期")
    
    # reconciliation_entries：当次对账写入的条目的标准化表示（JSON），用于撤销时基于内容匹配并注释
    reconciliation_entries = models.JSONField(null=True, blank=True, verbose_name="对账条目")

    # reconciliation_transaction_items：当次执行对账时的 transaction_items，用于撤销后预填
    reconciliation_transaction_items = models.JSONField(null=True, blank=True, verbose_name="对账差额分配条目")
    # revoked_task_id：撤销后新建或更新的待办指向被撤销的任务，用于 start 时取回预填数据
    revoked_task = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='revoked_task_follow_ups',
        verbose_name="被撤销的对账任务"
    )

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
        对于条目审核任务（entry_review）：一旦 status='pending' 则直接列出
        """
        from datetime import date
        queryset = cls.objects.filter(status='pending')
        if task_type:
            queryset = queryset.filter(task_type=task_type)
        
        # 条目审核待办不需要 scheduled_date 筛选，直接返回
        if task_type == 'entry_review':
            return queryset
        
        # 对账待办需要基于 scheduled_date 筛选
        if as_of_date is None:
            as_of_date = date.today()
        return queryset.filter(scheduled_date__lte=as_of_date)


class RecurringTask(BaseModel):
    """循环待办定义

    用户级别的循环待办定义，基于 rule_text（原始 DSL）与 rrule（归一化 RRULE）
    周期性地生成 ScheduledTask 实例。
    """

    RECURRENCE_BASIS_CHOICES = [
        ('scheduled', '按计划日期'),
        ('completed', '按完成日期'),
    ]

    STATUS_CHOICES = [
        ('active', '进行中'),
        ('paused', '已暂停'),
        ('ended', '已结束'),
    ]

    KIND_CHOICES = [
        ('notify', '通知'),
        ('generate_review', '生成审核待办'),
    ]

    user = models.ForeignKey(
        User,
        related_name='recurring_tasks',
        on_delete=models.CASCADE,
        db_index=True,
        verbose_name='属主'
    )
    title = models.CharField(max_length=128, verbose_name='标题')
    note = models.TextField(blank=True, default='', verbose_name='备注')
    kind = models.CharField(
        max_length=16,
        choices=KIND_CHOICES,
        default='notify',
        verbose_name='到期产出'
    )
    template_ref = models.CharField(
        max_length=128,
        blank=True,
        default='',
        verbose_name='模板引用（占位）'
    )
    rule_text = models.CharField(max_length=128, verbose_name='循环规则原文')
    rrule = models.CharField(max_length=256, verbose_name='归一化 RRULE')
    recurrence_basis = models.CharField(
        max_length=16,
        choices=RECURRENCE_BASIS_CHOICES,
        default='scheduled',
        verbose_name='循环基准'
    )
    start_date = models.DateField(verbose_name='基准日期')
    next_date = models.DateField(null=True, blank=True, verbose_name='下次生成日期')
    status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        default='active',
        verbose_name='状态'
    )
    last_generated_task = models.ForeignKey(
        'ScheduledTask',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        verbose_name='最近生成的实例'
    )
    generated_count = models.PositiveIntegerField(default=0, verbose_name='已生成实例数')

    class Meta:
        db_table = 'recurring_task'
        verbose_name = '循环待办定义'
        verbose_name_plural = verbose_name
        ordering = ['next_date']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status', 'next_date']),
        ]

    def __str__(self):
        return f'{self.title} ({self.get_status_display()})'
