from django.conf import settings
from django.db import models

from project.models import BaseModel


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
