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
