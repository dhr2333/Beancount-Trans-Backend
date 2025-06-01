from rest_framework import serializers
from translate.models import FormatConfig


class AnalyzeSerializer(serializers.Serializer):
    cmb_credit_ignore = serializers.CharField(required=False, allow_blank=False)
    boc_debit_ignore = serializers.CharField(required=False, allow_blank=False)
    write = serializers.BooleanField(required=False, default=False)
    password = serializers.CharField(required=False, allow_blank=True)
    balance = serializers.BooleanField(required=False, default=False)
    isCSVOnly = serializers.BooleanField(required=False, default=False)
    csrfmiddlewaretoken = serializers.CharField(required=False, allow_blank=False)


class FormatConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = FormatConfig
        fields = '__all__'
        read_only_fields = ('owner', 'id')  # 禁止修改所属用户

    def validate_flag(self, value):
        """验证标记符号有效性"""
        allowed_flags = ['*', '!', '#']
        if value not in allowed_flags:
            raise serializers.ValidationError(
                f"标记符号只能是 {', '.join(allowed_flags)} 中的一个"
            )
        return value

    def create(self, validated_data):
        """创建时自动关联当前用户"""
        user = self.context['request'].user
        return FormatConfig.objects.create(owner=user, **validated_data)