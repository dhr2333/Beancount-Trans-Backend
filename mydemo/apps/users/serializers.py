import re

from django.contrib.auth.models import Group
from rest_framework import serializers

from .models import User


class CreateUserSerializer(serializers.ModelSerializer):
    """注册序列化器"""
    password2 = serializers.CharField(label="确认密码", write_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "password", "password2", "mobile"]
        extra_kwage = {  # 修改字段选项
            "username": {
                "min_length": 5,
                "nax_length": 20,
                "error_message": {
                    "min_length": "仅允许5-20个字符的用户名",
                    "max_length": "仅允许5-20个字符的用户名",
                }
            },
            "password": {
                "write_only": True,
                "min_length": 8,
                "nax_length": 40,
                "error_message": {
                    "min_length": "仅允许8-40个字符的密码",
                    "max_length": "仅允许8-40个字符的密码",
                }
            }
        }

    def validated_mobile(self, value):
        """校验手机号格式"""
        if not re.match(r'1[3-9]\d{9}$', value):
            raise serializers.ValidationError("手机号格式有误")
        return value

    def validate(self, attrs):
        """校验两次密码是否相同"""
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError("两次密码不一致")
        return attrs

    def create(self, validated_date):
        del validated_date["password2"]  # 删除不需要存储的字段
        password = validated_date.pop("password")
        user = User(**validated_date)
        user.set_password(password)  # 对密码进行加密
        user.save()
        return user


class UserSerializer(serializers.HyperlinkedModelSerializer):
    expense = serializers.HyperlinkedRelatedField(many=True, view_name='expense-detail', read_only=True)
    assets = serializers.HyperlinkedRelatedField(many=True, view_name='assets-detail', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'url', 'username', 'email', 'mobile', 'expense', 'assets', 'income']


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = "__all__"
