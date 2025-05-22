from rest_framework import serializers

class LogDatesSerializer(serializers.Serializer):
    results = serializers.ListField(child=serializers.CharField())