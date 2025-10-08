from rest_framework import serializers
from project.apps.tags.models import Tag


class TagTreeSerializer(serializers.ModelSerializer):
    """标签树形结构序列化器"""
    children = serializers.SerializerMethodField()
    parent_name = serializers.CharField(source='parent.name', read_only=True)
    full_path = serializers.SerializerMethodField()
    
    class Meta:
        model = Tag
        fields = [
            'id', 'name', 'parent', 'parent_name', 'full_path',
            'description', 'owner', 'enable',
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


class TagSerializer(serializers.ModelSerializer):
    """标签基础序列化器"""
    parent_name = serializers.CharField(source='parent.name', read_only=True)
    full_path = serializers.SerializerMethodField()
    has_children = serializers.SerializerMethodField()
    
    class Meta:
        model = Tag
        fields = [
            'id', 'name', 'parent', 'parent_name', 'full_path',
            'description', 'owner', 'enable', 'has_children',
            'created', 'modified'
        ]
        read_only_fields = ['id', 'created', 'modified', 'owner']
    
    def get_full_path(self, obj):
        """获取标签的完整路径"""
        return obj.get_full_path()
    
    def get_has_children(self, obj):
        """检查是否有子标签"""
        return obj.has_children()
    
    def validate_name(self, value):
        """验证标签名称格式"""
        # 标签名称不能包含空格、#号等特殊字符
        if not value or not value.strip():
            raise serializers.ValidationError("标签名称不能为空")
        
        # 检查是否包含非法字符
        invalid_chars = [' ', '#', '\n', '\r', '\t']
        for char in invalid_chars:
            if char in value:
                raise serializers.ValidationError(f"标签名称不能包含字符: '{char}'")
        
        return value.strip()
    
    def validate(self, data):
        """验证整体数据"""
        # 如果指定了父标签，检查父标签是否启用
        parent = data.get('parent')
        if parent and not parent.enable:
            raise serializers.ValidationError("父标签已禁用，无法创建子标签")
        
        return data


class TagBatchUpdateSerializer(serializers.Serializer):
    """标签批量更新序列化器"""
    tag_ids = serializers.ListField(
        child=serializers.IntegerField(),
        help_text="要更新的标签ID列表"
    )
    action = serializers.ChoiceField(
        choices=['enable', 'disable', 'delete'],
        help_text="操作类型"
    )
    
    def validate_tag_ids(self, value):
        """验证标签ID列表"""
        if not value:
            raise serializers.ValidationError("标签ID列表不能为空")
        return value


class TagDeleteSerializer(serializers.Serializer):
    """标签删除序列化器"""
    force = serializers.BooleanField(
        default=False,
        help_text="是否强制删除（包括子标签和映射关联）"
    )


