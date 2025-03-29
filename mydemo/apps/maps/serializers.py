from rest_framework import serializers
from django.contrib.auth import get_user_model

from translate.models import Expense, Assets, Income, FormatConfig


class ExpenseSerializer(serializers.HyperlinkedModelSerializer):
    payee = serializers.CharField(allow_blank=True, allow_null=True)
    currency = serializers.CharField(allow_blank=True, allow_null=True)
    owner = serializers.ReadOnlyField(source='owner.username')

    # mobile = serializers.ReadOnlyField(source='owner.mobile')

    class Meta:
        model = Expense
        fields = ['id', 'url', 'owner', 'key', 'payee', 'expend', 'currency']


class AssetsSerializer(serializers.HyperlinkedModelSerializer):
    owner = serializers.ReadOnlyField(source='owner.username')

    # mobile = serializers.ReadOnlyField(source='owner.mobile')

    class Meta:
        model = Assets
        fields = ['id', 'url', 'owner', 'key', 'full', 'assets']


class IncomeSerializer(serializers.HyperlinkedModelSerializer):
    owner = serializers.ReadOnlyField(source='owner.username')

    # mobile = serializers.ReadOnlyField(source='owner.mobile')

    class Meta:
        model = Income
        fields = ['id', 'url', 'owner', 'key', 'payer', 'income']


User = get_user_model()

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