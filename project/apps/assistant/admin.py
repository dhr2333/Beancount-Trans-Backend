from django.contrib import admin

from .models import AssistantFeedback


@admin.register(AssistantFeedback)
class AssistantFeedbackAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'rating',
        'short_user_message',
        'short_comment',
        'created',
    )
    list_filter = ('rating', 'created')
    search_fields = ('user__username', 'user_message', 'assistant_reply', 'comment')
    readonly_fields = ('created', 'modified')
    ordering = ('-created',)

    @admin.display(description='用户问题')
    def short_user_message(self, obj: AssistantFeedback) -> str:
        text = obj.user_message or ''
        return text if len(text) <= 60 else f'{text[:60]}...'

    @admin.display(description='反馈原因')
    def short_comment(self, obj: AssistantFeedback) -> str:
        text = obj.comment or ''
        if not text:
            return '-'
        return text if len(text) <= 40 else f'{text[:40]}...'
