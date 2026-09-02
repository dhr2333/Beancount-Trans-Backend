from rest_framework import serializers

from .models import ChatMessage, ChatSession


class ChatMessageSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=['user', 'assistant'])
    content = serializers.CharField(max_length=4000)


class AssistantChatRequestSerializer(serializers.Serializer):
    messages = ChatMessageSerializer(many=True, required=False)
    session_id = serializers.UUIDField(required=False, allow_null=True)
    content = serializers.CharField(max_length=4000, required=False, allow_blank=False)
    edit_message_id = serializers.UUIDField(required=False, allow_null=True)
    show_bql = serializers.BooleanField(default=False, required=False)
    deep_think = serializers.BooleanField(default=False, required=False)

    def validate(self, attrs):
        messages = attrs.get('messages')
        session_id = attrs.get('session_id')
        content = attrs.get('content')
        edit_message_id = attrs.get('edit_message_id')

        if edit_message_id is not None and session_id is None:
            raise serializers.ValidationError({'edit_message_id': '编辑消息需要提供 session_id'})

        if session_id is not None or content:
            if not content or not str(content).strip():
                raise serializers.ValidationError({'content': '消息内容不能为空'})
            return attrs

        if not messages:
            raise serializers.ValidationError('需要提供 messages，或 session_id 与 content')

        if not any(msg['role'] == 'user' for msg in messages):
            raise serializers.ValidationError({'messages': '至少需要一条用户消息'})
        return attrs


class QueryRecordSerializer(serializers.Serializer):
    bql = serializers.CharField()
    result_preview = serializers.CharField()


class AssistantChatResponseSerializer(serializers.Serializer):
    reply = serializers.CharField()
    queries = QueryRecordSerializer(many=True)
    thinking = serializers.CharField(allow_blank=True, required=False, default='')
    reasoning = serializers.CharField(allow_blank=True, required=False, default='')
    model = serializers.CharField(allow_blank=True, required=False, default='')
    session_id = serializers.UUIDField(required=False, allow_null=True)
    user_message_id = serializers.UUIDField(required=False, allow_null=True)
    assistant_message_id = serializers.UUIDField(required=False, allow_null=True)


class AssistantKeyTestRequestSerializer(serializers.Serializer):
    api_key = serializers.CharField(required=False, allow_blank=True, default='')
    base_url = serializers.CharField(required=False, allow_blank=True, default='')
    model = serializers.CharField(required=False, allow_blank=True, default='')


class AssistantKeyTestResponseSerializer(serializers.Serializer):
    ok = serializers.BooleanField()
    copilot_available = serializers.BooleanField()
    parse_available = serializers.BooleanField()
    detail = serializers.CharField()


class AssistantStatusSerializer(serializers.Serializer):
    api_key_configured = serializers.BooleanField()
    assistant_model = serializers.CharField(allow_blank=True, required=False, default='')
    deep_think_supported = serializers.BooleanField()
    ledger_exists = serializers.BooleanField()
    ledger_path = serializers.CharField(allow_blank=True)
    reference_date = serializers.DateField(help_text='助手使用的基准日期（今天）')


class AssistantFeedbackRequestSerializer(serializers.Serializer):
    message_id = serializers.UUIDField()
    rating = serializers.ChoiceField(
        choices=['like', 'dislike'],
        allow_null=True,
        required=False,
    )
    user_message = serializers.CharField(max_length=4000)
    assistant_reply = serializers.CharField()
    queries = QueryRecordSerializer(many=True, required=False, default=list)
    comment = serializers.CharField(max_length=500, required=False, allow_blank=True, default='')


class AssistantFeedbackResponseSerializer(serializers.Serializer):
    message_id = serializers.UUIDField()
    rating = serializers.ChoiceField(choices=['like', 'dislike'], allow_null=True)
    comment = serializers.CharField(allow_blank=True, required=False)


class ChatSessionListSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatSession
        fields = ('id', 'title', 'created', 'modified')


class StoredChatMessageSerializer(serializers.ModelSerializer):
    feedback = serializers.SerializerMethodField()

    class Meta:
        model = ChatMessage
        fields = (
            'id',
            'role',
            'content',
            'thinking',
            'reasoning',
            'queries',
            'position',
            'generation_status',
            'feedback',
            'created',
        )

    def get_feedback(self, obj: ChatMessage):
        feedback_map = self.context.get('feedback_map', {})
        return feedback_map.get(str(obj.id))


class ChatSessionDetailSerializer(serializers.ModelSerializer):
    messages = serializers.SerializerMethodField()

    class Meta:
        model = ChatSession
        fields = ('id', 'title', 'title_locked', 'created', 'modified', 'messages')

    def get_messages(self, obj: ChatSession):
        message_rows = list(obj.messages.order_by('position'))
        feedback_map = self.context.get('feedback_map', {})
        return StoredChatMessageSerializer(
            message_rows,
            many=True,
            context={'feedback_map': feedback_map},
        ).data


class ChatSessionUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatSession
        fields = ('title',)

    def validate_title(self, value: str) -> str:
        title = (value or '').strip()
        if not title:
            raise serializers.ValidationError('标题不能为空')
        return title[:120]
