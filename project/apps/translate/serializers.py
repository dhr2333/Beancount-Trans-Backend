from rest_framework import serializers

class AnalyzeSerializer(serializers.Serializer):
    password = serializers.CharField(required=False, allow_blank=True)
    isCSVOnly = serializers.BooleanField(required=False, default=False)
    balance = serializers.BooleanField(required=False, default=False)
    write = serializers.BooleanField(required=False, default=False)
    # 其他参数
