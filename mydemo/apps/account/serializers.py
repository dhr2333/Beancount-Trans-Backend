from rest_framework import serializers

from .models import Account


class AccountSerializer(serializers.HyperlinkedModelSerializer):
    owner = serializers.ReadOnlyField(source='owner.username')

    class Meta:
        model = Account
        fields = ['id', 'url', 'owner', 'date', 'status', 'account', 'currency', 'note', 'account_type']
