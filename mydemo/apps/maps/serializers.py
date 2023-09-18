from rest_framework import serializers

from translate.models import Expense, Assets


class ExpenseSerializer(serializers.HyperlinkedModelSerializer):
    payee = serializers.CharField(allow_blank=True, allow_null=True)
    owner = serializers.ReadOnlyField(source='owner.username')

    # mobile = serializers.ReadOnlyField(source='owner.mobile')

    class Meta:
        model = Expense
        fields = ['id', 'url', 'owner', 'key', 'payee', 'expend', 'tag', 'classification']


class AssetsSerializer(serializers.HyperlinkedModelSerializer):
    owner = serializers.ReadOnlyField(source='owner.username')

    # mobile = serializers.ReadOnlyField(source='owner.mobile')

    class Meta:
        model = Assets
        fields = ['id', 'url', 'owner', 'key', 'full', 'income']
