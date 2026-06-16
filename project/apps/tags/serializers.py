from django.db import IntegrityError
from rest_framework import serializers

from project.apps.tags.models import Tag

_DUPLICATE_TAG_MSG = '该标签已存在，请勿重复添加'


class TagTreeSerializer(serializers.ModelSerializer):
    """标签树形结构序列化器"""
    children = serializers.SerializerMethodField()
    parent_name = serializers.CharField(source='parent.name', read_only=True)
    full_path = serializers.SerializerMethodField()
    mapping_count = serializers.SerializerMethodField()

    class Meta:
        model = Tag
        fields = [
            'id', 'name', 'parent', 'parent_name', 'full_path',
            'description', 'owner', 'enable', 'mapping_count',
            'children', 'created', 'modified'
        ]
        read_only_fields = ['id', 'created', 'modified', 'owner']

    def get_children(self, obj):
        """递归获取子标签"""
        children = obj.children.all().order_by('name')
        if children.exists():
            return TagTreeSerializer(children, many=True, context=self.context).data
        return []

    def get_full_path(self, obj):
        """获取标签的完整路径，如 Category/EDUCATION"""
        return obj.get_full_path()

    def get_mapping_count(self, obj):
        """获取使用此标签的映射数量（参考 Account 的实现）"""
        try:
            from django.apps import apps

            # 获取映射模型
            Expense = apps.get_model('maps', 'Expense')
            Assets = apps.get_model('maps', 'Assets')
            Income = apps.get_model('maps', 'Income')

            # 获取当前用户
            request = self.context.get('request')
            if not request:
                return {'expense': 0, 'assets': 0, 'income': 0, 'total': 0}

            from django.contrib.auth import get_user_model
            User = get_user_model()

            if request.user.is_authenticated:
                user = request.user
            else:
                # 匿名用户使用id=1用户的数据
                try:
                    user = User.objects.get(id=1)
                except User.DoesNotExist:
                    return {'expense': 0, 'assets': 0, 'income': 0, 'total': 0}

            # 统计使用此标签的映射数量
            expense_count = Expense.objects.filter(tags=obj, owner=user).count()
            assets_count = Assets.objects.filter(tags=obj, owner=user).count()
            income_count = Income.objects.filter(tags=obj, owner=user).count()

            return {
                'expense': expense_count,
                'assets': assets_count,
                'income': income_count,
                'total': expense_count + assets_count + income_count
            }
        except Exception as e:
            return {'expense': 0, 'assets': 0, 'income': 0, 'total': 0}


class TagSerializer(serializers.ModelSerializer):
    """标签基础序列化器"""
    parent_name = serializers.CharField(source='parent.name', read_only=True)
    full_path = serializers.SerializerMethodField()
    has_children = serializers.SerializerMethodField()
    mapping_count = serializers.SerializerMethodField()

    class Meta:
        model = Tag
        fields = [
            'id', 'name', 'parent', 'parent_name', 'full_path',
            'description', 'owner', 'enable', 'has_children', 'mapping_count',
            'created', 'modified'
        ]
        read_only_fields = ['id', 'created', 'modified', 'owner', 'parent']

    def get_full_path(self, obj):
        """获取标签的完整路径"""
        return obj.get_full_path()

    def get_has_children(self, obj):
        """检查是否有子标签"""
        return obj.has_children()

    def get_mapping_count(self, obj):
        """获取使用此标签的映射数量"""
        try:
            from django.apps import apps

            # 获取映射模型
            Expense = apps.get_model('maps', 'Expense')
            Assets = apps.get_model('maps', 'Assets')
            Income = apps.get_model('maps', 'Income')

            # 获取当前用户
            request = self.context.get('request')
            if not request:
                return {'expense': 0, 'assets': 0, 'income': 0, 'total': 0}

            from django.contrib.auth import get_user_model
            User = get_user_model()

            if request.user.is_authenticated:
                user = request.user
            else:
                try:
                    user = User.objects.get(id=1)
                except User.DoesNotExist:
                    return {'expense': 0, 'assets': 0, 'income': 0, 'total': 0}

            # 统计使用此标签的映射数量
            expense_count = Expense.objects.filter(tags=obj, owner=user).count()
            assets_count = Assets.objects.filter(tags=obj, owner=user).count()
            income_count = Income.objects.filter(tags=obj, owner=user).count()

            return {
                'expense': expense_count,
                'assets': assets_count,
                'income': income_count,
                'total': expense_count + assets_count + income_count
            }
        except Exception:
            return {'expense': 0, 'assets': 0, 'income': 0, 'total': 0}

    def validate_name(self, value):
        """验证标签名称格式

        支持两种输入方式：
        1. 完整路径：Project/Decoration（自动创建父标签）
        2. 单个名称：Irregular（无父标签）
        """
        if not value or not value.strip():
            raise serializers.ValidationError("标签名称不能为空")

        # 检查是否包含非法字符（斜杠除外，用于路径）
        invalid_chars = [' ', '#', '\n', '\r', '\t']
        for char in invalid_chars:
            if char in value:
                raise serializers.ValidationError(f"标签名称不能包含字符: '{char}'")

        path = value.strip()
        request = self.context.get('request')
        if request and getattr(request.user, 'is_authenticated', False):
            if self._tag_with_path_exists(path, request.user):
                raise serializers.ValidationError(_DUPLICATE_TAG_MSG)

        return path

    def _tag_with_path_exists(self, path, owner):
        """检查指定完整路径的标签是否已存在"""
        leaf_name = path.split('/')[-1] if '/' in path else path
        qs = Tag.objects.filter(name=leaf_name, owner=owner)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        return any(tag.get_full_path() == path for tag in qs)

    def _get_or_create_parent_by_path(self, owner, parent_path):
        """根据完整路径查找或创建父标签"""
        helper = Tag(owner=owner, name='__helper__')
        try:
            return helper._get_tag_by_path(parent_path)
        except Tag.DoesNotExist:
            return helper._create_parent_tag(parent_path)

    def _apply_path_to_instance(self, instance, path):
        """将完整路径解析为叶子名称与父标签"""
        if '/' in path:
            instance.name = path.split('/')[-1]
            parent_path = '/'.join(path.split('/')[:-1])
            parent = self._get_or_create_parent_by_path(instance.owner, parent_path)
            if parent.pk == instance.pk:
                raise serializers.ValidationError({'name': '标签不能成为自己的父标签'})
            instance.parent = parent
        else:
            instance.name = path
            instance.parent = None

    def create(self, validated_data):
        try:
            return super().create(validated_data)
        except IntegrityError:
            raise serializers.ValidationError({'name': [_DUPLICATE_TAG_MSG]})

    def update(self, instance, validated_data):
        name_input = validated_data.pop('name', None)
        if name_input is not None:
            new_path = name_input.strip()
            if new_path != instance.get_full_path():
                self._apply_path_to_instance(instance, new_path)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        try:
            instance.save()
        except IntegrityError:
            raise serializers.ValidationError({'name': [_DUPLICATE_TAG_MSG]})
        return instance

    def validate(self, data):
        """验证整体数据"""
        # 如果指定了父标签，检查父标签是否启用
        parent = data.get('parent')
        if parent and not parent.enable:
            raise serializers.ValidationError("父标签已禁用，无法创建子标签")

        return data


class TagDeleteSerializer(serializers.Serializer):
    """标签删除序列化器"""
    force = serializers.BooleanField(
        default=False,
        help_text="是否强制删除（包括子标签和映射关联）"
    )



