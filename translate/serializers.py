from rest_framework import serializers

from .models import Expense_Map, Assets_Map


class ExpenseMapSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense_Map
        fields = "__all__"


class AssetsMapSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assets_Map
        fields = "__all__"
