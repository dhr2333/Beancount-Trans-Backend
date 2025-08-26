from rest_framework import serializers
from project.apps.maps.models import Expense, Assets, Income, Template, TemplateItem


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


class TemplateItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = TemplateItem
        fields = '__all__'
        read_only_fields = ('created', 'modified')


class TemplateSerializer(serializers.ModelSerializer):
    items = TemplateItemSerializer(many=True, required=False)
    owner_name = serializers.CharField(source='owner.username', read_only=True)
    
    class Meta:
        model = Template
        fields = '__all__'
        read_only_fields = ('created', 'modified', 'owner')
    
    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        template = Template.objects.create(**validated_data)
        
        for item_data in items_data:
            TemplateItem.objects.create(template=template, **item_data)
            
        return template
    
    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', [])
        
        # 更新模板基本信息
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # 处理模板项 - 先删除所有现有项，然后重新创建
        instance.items.all().delete()
        for item_data in items_data:
            TemplateItem.objects.create(template=instance, **item_data)
            
        return instance


class TemplateApplySerializer(serializers.Serializer):
    """非模型序列化器，因为应用模板的操作不直接对应模型的创建或更新，而是触发一个动作（应用模板到用户映射）"""
    
    template_id = serializers.IntegerField()
    action = serializers.ChoiceField(choices=['overwrite', 'merge'])
    conflict_resolution = serializers.ChoiceField(
        choices=['skip', 'overwrite'], 
        required=False,
        default='skip'
    )