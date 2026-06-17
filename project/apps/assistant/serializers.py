from rest_framework import serializers


class ChatMessageSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=['user', 'assistant'])
    content = serializers.CharField(max_length=4000)


class AssistantChatRequestSerializer(serializers.Serializer):
    messages = ChatMessageSerializer(many=True, min_length=1, max_length=20)
    show_bql = serializers.BooleanField(default=False, required=False)

    def validate_messages(self, value):
        if not any(msg['role'] == 'user' for msg in value):
            raise serializers.ValidationError('至少需要一条用户消息')
        return value


class QueryRecordSerializer(serializers.Serializer):
    bql = serializers.CharField()
    result_preview = serializers.CharField()


class AssistantChatResponseSerializer(serializers.Serializer):
    reply = serializers.CharField()
    queries = QueryRecordSerializer(many=True)
    api_key_source = serializers.ChoiceField(choices=['user', 'platform', 'none'])
    thinking = serializers.CharField(allow_blank=True, required=False, default='')
    reasoning = serializers.CharField(allow_blank=True, required=False, default='')


class AssistantStatusSerializer(serializers.Serializer):
    api_key_configured = serializers.BooleanField()
    api_key_source = serializers.ChoiceField(choices=['user', 'platform', 'none'])
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
