from django.contrib import admin

from .models import AssistantFeedback, ChatMessage, ChatSession

MODE_LABELS = {
    'normal': '常规',
    'plain': '简明',
    'insight': '洞察',
    'bookkeeping': '记账',
}


def format_modes(modes) -> str:
    """把模式标签列表渲染成中文展示文本。"""
    values = [str(mode) for mode in (modes or [])]
    return '、'.join(MODE_LABELS.get(mode, mode) for mode in values) or '-'


class MessageModeFilter(admin.SimpleListFilter):
    title = '应答模式'
    parameter_name = 'mode'

    def lookups(self, request, model_admin):
        return list(MODE_LABELS.items())

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(modes__contains=[self.value()])
        return queryset


class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 0
    readonly_fields = ('id', 'role', 'position', 'modes_display', 'created')
    fields = ('position', 'role', 'content', 'modes_display', 'created')
    ordering = ('position',)

    @admin.display(description='应答模式')
    def modes_display(self, obj: ChatMessage) -> str:
        return format_modes(obj.modes)


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'title', 'title_locked', 'modified', 'created')
    list_filter = ('title_locked', 'created')
    search_fields = ('title', 'user__username')
    readonly_fields = ('created', 'modified')
    ordering = ('-modified',)
    inlines = [ChatMessageInline]


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'session',
        'position',
        'role',
        'modes_display',
        'generation_status',
        'created',
    )
    list_filter = ('role', 'generation_status', MessageModeFilter)
    search_fields = ('session__user__username', 'content')
    readonly_fields = ('created', 'modified')
    ordering = ('-created',)

    @admin.display(description='应答模式')
    def modes_display(self, obj: ChatMessage) -> str:
        return format_modes(obj.modes)


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
