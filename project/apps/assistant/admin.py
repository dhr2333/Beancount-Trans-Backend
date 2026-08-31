from django.contrib import admin

from .models import AssistantFeedback, ChatMessage, ChatSession


class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 0
    readonly_fields = ('id', 'role', 'position', 'created')
    fields = ('position', 'role', 'content', 'created')
    ordering = ('position',)


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'title', 'title_locked', 'modified', 'created')
    list_filter = ('title_locked', 'created')
    search_fields = ('title', 'user__username')
    readonly_fields = ('created', 'modified')
    ordering = ('-modified',)
    inlines = [ChatMessageInline]


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
