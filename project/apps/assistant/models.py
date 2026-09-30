import uuid

from django.conf import settings
from django.db import models

from project.models import BaseModel


class ChatSession(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='assistant_sessions',
    )
    title = models.CharField(max_length=120, blank=True, default='')
    title_locked = models.BooleanField(default=False)
    shared_binding_ids = models.JSONField(
        default=list,
        blank=True,
        verbose_name='会话纳入的共享账本绑定',
    )

    class Meta:
        verbose_name = '助手会话'
        verbose_name_plural = '助手会话'
        ordering = ['-modified']
        indexes = [
            models.Index(fields=['user', '-modified']),
        ]

    def __str__(self) -> str:
        return f'{self.user_id} {self.title or self.id}'


class ChatMessage(BaseModel):
    ROLE_USER = 'user'
    ROLE_ASSISTANT = 'assistant'
    ROLE_CHOICES = [
        (ROLE_USER, '用户'),
        (ROLE_ASSISTANT, '助手'),
    ]

    STATUS_GENERATING = 'generating'
    STATUS_COMPLETE = 'complete'
    STATUS_CANCELLED = 'cancelled'
    STATUS_FAILED = 'failed'
    GENERATION_STATUS_CHOICES = [
        (STATUS_GENERATING, '生成中'),
        (STATUS_COMPLETE, '已完成'),
        (STATUS_CANCELLED, '已取消'),
        (STATUS_FAILED, '失败'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name='messages',
    )
    role = models.CharField(max_length=16, choices=ROLE_CHOICES)
    content = models.TextField()
    thinking = models.TextField(blank=True, default='')
    reasoning = models.TextField(blank=True, default='')
    queries = models.JSONField(default=list, blank=True)
    modes = models.JSONField(
        default=list,
        blank=True,
        verbose_name='应答模式',
        help_text='本条回复使用的模式标签，如 normal/plain/insight/bookkeeping',
    )
    position = models.PositiveIntegerField()
    generation_status = models.CharField(
        max_length=16,
        choices=GENERATION_STATUS_CHOICES,
        default=STATUS_COMPLETE,
    )
    celery_task_id = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        verbose_name = '助手消息'
        verbose_name_plural = '助手消息'
        ordering = ['position']
        indexes = [
            models.Index(fields=['session', 'position']),
        ]

    def __str__(self) -> str:
        return f'{self.session_id} {self.role} #{self.position}'


class AssistantFeedback(BaseModel):
    RATING_LIKE = 'like'
    RATING_DISLIKE = 'dislike'
    RATING_CHOICES = [
        (RATING_LIKE, '喜欢'),
        (RATING_DISLIKE, '不喜欢'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='assistant_feedbacks',
    )
    message_id = models.UUIDField()
    rating = models.CharField(max_length=8, choices=RATING_CHOICES)
    user_message = models.TextField()
    assistant_reply = models.TextField()
    queries = models.JSONField(default=list, blank=True)
    comment = models.TextField(blank=True)

    class Meta:
        verbose_name = '助手回复反馈'
        verbose_name_plural = '助手回复反馈'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'message_id'],
                name='assistant_feedback_user_message_unique',
            ),
        ]
        indexes = [
            models.Index(fields=['user', 'rating']),
            models.Index(fields=['created']),
        ]

    def __str__(self) -> str:
        return f'{self.user_id} {self.rating} {self.message_id}'


class SharedLedgerBinding(BaseModel):
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='shared_ledger_bindings',
        verbose_name='接收方',
    )
    token = models.ForeignKey(
        'authentication.PersonalAccessToken',
        on_delete=models.CASCADE,
        related_name='ledger_bindings',
        verbose_name='访问令牌',
    )
    aliases = models.JSONField(
        default=list,
        blank=True,
        verbose_name='别名',
        help_text='Copilot 可用其中任意一个别名识别这个共享账本；可为空，为空时用来源用户名',
    )
    last_used_at = models.DateTimeField(null=True, blank=True, verbose_name='最后使用时间')

    class Meta:
        verbose_name = '共享账本绑定'
        verbose_name_plural = verbose_name
        ordering = ['-created']
        constraints = [
            models.UniqueConstraint(
                fields=['recipient', 'token'],
                name='shared_ledger_binding_recipient_token_unique',
            ),
        ]
        indexes = [
            models.Index(fields=['recipient']),
        ]

    def __str__(self) -> str:
        return f'{self.recipient_id} -> {self.token_id} ({self.aliases})'

    @property
    def owner(self):
        return self.token.user

    def is_usable(self) -> bool:
        return self.token.is_usable() and self.token.user.is_active
