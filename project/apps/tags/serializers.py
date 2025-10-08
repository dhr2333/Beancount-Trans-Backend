from rest_framework import serializers
from project.apps.tags.models import Tag


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



