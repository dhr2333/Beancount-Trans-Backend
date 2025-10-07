from rest_framework import serializers
from project.apps.maps.models import Expense, Assets, Income, Template, TemplateItem
from project.apps.account.models import Account


class AccountSummarySerializer(serializers.ModelSerializer):
    """账户摘要序列化器，用于在映射中显示账户信息"""
    class Meta:
        model = Account
        fields = ['id', 'account', 'enable']


class ExpenseSerializer(serializers.ModelSerializer):
    payee = serializers.CharField(allow_blank=True, allow_null=True)
    
    # 读取时显示详细信息
    expend = AccountSummarySerializer(read_only=True)
    
    # 写入时使用ID
    expend_id = serializers.PrimaryKeyRelatedField(
        queryset=Account.objects.all(),
        source='expend',
        write_only=True,
        required=False,
        allow_null=True
    )
    
    owner = serializers.ReadOnlyField(source='owner.username')
    enable = serializers.BooleanField(default=True, help_text="是否启用", required=False)

    class Meta:
        model = Expense
        fields = ['id', 'owner', 'key', 'payee', 'expend', 'expend_id', 'currency', 'enable']
        extra_kwargs = {
            'key': {'required': False}  # 允许更新时不传 key
        }


class AssetsSerializer(serializers.ModelSerializer):
    # 读取时显示详细信息
    assets = AccountSummarySerializer(read_only=True)
    
    # 写入时使用ID
    assets_id = serializers.PrimaryKeyRelatedField(
        queryset=Account.objects.all(),
        source='assets',
        write_only=True,
        required=False,
        allow_null=True
    )
    
    owner = serializers.ReadOnlyField(source='owner.username')
    enable = serializers.BooleanField(default=True, help_text="是否启用", required=False)

    class Meta:
        model = Assets
        fields = ['id', 'owner', 'key', 'full', 'assets', 'assets_id', 'enable']


class IncomeSerializer(serializers.ModelSerializer):
    # 读取时显示详细信息
    income = AccountSummarySerializer(read_only=True)
    
    # 写入时使用ID
    income_id = serializers.PrimaryKeyRelatedField(
        queryset=Account.objects.all(),
        source='income',
        write_only=True,
        required=False,
        allow_null=True
    )
    
    owner = serializers.ReadOnlyField(source='owner.username')
    enable = serializers.BooleanField(default=True, help_text="是否启用", required=False)

    class Meta:
        model = Income
        fields = ['id', 'owner', 'key', 'payer', 'income', 'income_id', 'enable']


class TemplateItemSerializer(serializers.ModelSerializer):
    # 读取时显示详细信息
    account = AccountSummarySerializer(read_only=True)
    
    # 写入时使用ID
    account_id = serializers.PrimaryKeyRelatedField(
        queryset=Account.objects.all(),
        source='account',
        write_only=True,
        required=False,
        allow_null=True
    )
    
    class Meta:
        model = TemplateItem
        fields = '__all__'
        read_only_fields = ('created', 'modified')


class TemplateListSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source='owner.username', read_only=True)

    class Meta:
        model = Template
        fields = ['id', 'name', 'description', 'type', 'is_public', 'is_official', 
                 'version', 'update_notes', 'owner', 'owner_name', 'created', 'modified']
        read_only_fields = ('created', 'modified', 'owner')


class TemplateDetailSerializer(serializers.ModelSerializer):
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


class ExpenseBatchUpdateSerializer(serializers.Serializer):
    """支出映射批量更新序列化器"""
    expense_ids = serializers.ListField(
        child=serializers.IntegerField(),
        help_text="要更新的支出映射ID列表"
    )
    expend_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="新的支出账户ID"
    )
    currency = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        max_length=24,
        help_text="新的货币代码"
    )
    
    def validate_expense_ids(self, value):
        """验证支出映射ID列表"""
        if not value:
            raise serializers.ValidationError("支出映射ID列表不能为空")
        return value
    
    def validate(self, data):
        """验证整体数据"""
        expend_id = data.get('expend_id')
        currency = data.get('currency')
        
        if expend_id is None and currency is None:
            raise serializers.ValidationError("至少需要指定一个要更新的字段")
        
        return data


class TemplateApplySerializer(serializers.Serializer):
    """非模型序列化器，因为应用模板的操作不直接对应模型的创建或更新，而是触发一个动作（应用模板到用户映射）"""
    
    template_id = serializers.IntegerField()
    action = serializers.ChoiceField(choices=['overwrite', 'merge'])
    conflict_resolution = serializers.ChoiceField(
        choices=['skip', 'overwrite'], 
        required=False,
        default='skip'
    )
