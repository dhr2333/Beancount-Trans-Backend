from rest_framework import serializers
# from django.contrib.auth import get_user_model

from maps.models import Expense, Assets, Income


class ExpenseSerializer(serializers.HyperlinkedModelSerializer):
    payee = serializers.CharField(allow_blank=True, allow_null=True)
    currency = serializers.CharField(allow_blank=True, allow_null=True)
    owner = serializers.ReadOnlyField(source='owner.username')
    enable = serializers.BooleanField(default=True, help_text="是否启用", required=False)

    # mobile = serializers.ReadOnlyField(source='owner.mobile')

    class Meta:
        model = Expense
        fields = ['id', 'url', 'owner', 'key', 'payee', 'expend', 'currency', 'enable']
        extra_kwargs = {
            'key': {'required': False}  # 允许更新时不传 key
        }


class AssetsSerializer(serializers.HyperlinkedModelSerializer):
    owner = serializers.ReadOnlyField(source='owner.username')
    enable = serializers.BooleanField(default=True, help_text="是否启用", required=False)

    # mobile = serializers.ReadOnlyField(source='owner.mobile')

    class Meta:
        model = Assets
        fields = ['id', 'url', 'owner', 'key', 'full', 'assets', 'enable']


class IncomeSerializer(serializers.HyperlinkedModelSerializer):
    owner = serializers.ReadOnlyField(source='owner.username')
    enable = serializers.BooleanField(default=True, help_text="是否启用", required=False)

    # mobile = serializers.ReadOnlyField(source='owner.mobile')

    class Meta:
        model = Income
        fields = ['id', 'url', 'owner', 'key', 'payer', 'income', 'enable']


# User = get_user_model()

