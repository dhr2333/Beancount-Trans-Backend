from rest_framework import serializers
# from django.contrib.auth.models import User
from project.apps.account.models import Account


class AccountTreeSerializer(serializers.ModelSerializer):
    """账户树形结构序列化器"""
    children = serializers.SerializerMethodField()
    parent_account = serializers.CharField(source='parent.account', read_only=True)
    account_type = serializers.CharField(source='get_account_type', read_only=True)
    mapping_count = serializers.SerializerMethodField()

    class Meta:
        model = Account
        fields = [
            'id', 'account', 'parent', 'parent_account',
            'owner', 'enable', 'account_type', 'mapping_count',
            'children', 'created', 'modified'
        ]
        read_only_fields = ['id', 'created', 'modified', 'owner']

    def get_children(self, obj):
        """递归获取子账户"""
        children = obj.children.all().order_by('account')
        if children.exists():
            return AccountTreeSerializer(children, many=True, context=self.context).data
        return []

    def get_mapping_count(self, obj):
        """获取与此账户相关的映射数量"""
        from django.apps import apps

        try:
            Expense = apps.get_model('maps', 'Expense')
            Assets = apps.get_model('maps', 'Assets')
            Income = apps.get_model('maps', 'Income')

            # 获取当前用户，匿名用户使用id=1用户的数据
            request = self.context.get('request')
            if not request:
                return {'expense': 0, 'assets': 0, 'income': 0, 'total': 0}

            from django.contrib.auth import get_user_model
            User = get_user_model()

            if request.user.is_authenticated:
                user = request.user
            else:
                # 匿名用户使用id=1用户的映射
                try:
                    user = User.objects.get(id=1)
                except User.DoesNotExist:
                    return {'expense': 0, 'assets': 0, 'income': 0, 'total': 0}

            # 统计用户的所有映射记录（包括已关闭的）
            expense_count = Expense.objects.filter(expend=obj, owner=user).count()
            assets_count = Assets.objects.filter(assets=obj, owner=user).count()
            income_count = Income.objects.filter(income=obj, owner=user).count()

            return {
                'expense': expense_count,
                'assets': assets_count,
                'income': income_count,
                'total': expense_count + assets_count + income_count
            }
        except:
            return {'expense': 0, 'assets': 0, 'income': 0, 'total': 0}


class AccountSerializer(serializers.ModelSerializer):
    """账户基础序列化器"""
    parent_account = serializers.CharField(source='parent.account', read_only=True)
    account_type = serializers.CharField(source='get_account_type', read_only=True)
    has_children = serializers.BooleanField(read_only=True)
    mapping_count = serializers.SerializerMethodField()

    class Meta:
        model = Account
        fields = [
            'id', 'account', 'parent', 'parent_account',
            'owner', 'enable', 'account_type', 'has_children', 'mapping_count',
            'created', 'modified'
        ]
        read_only_fields = ['id', 'created', 'modified', 'owner']

    def get_mapping_count(self, obj):
        """获取与此账户相关的映射数量"""
        from django.apps import apps

        try:
            Expense = apps.get_model('maps', 'Expense')
            Assets = apps.get_model('maps', 'Assets')
            Income = apps.get_model('maps', 'Income')

            # 获取当前用户，匿名用户使用id=1用户的数据
            request = self.context.get('request')
            if not request:
                return {'expense': 0, 'assets': 0, 'income': 0, 'total': 0}

            from django.contrib.auth import get_user_model
            User = get_user_model()

            if request.user.is_authenticated:
                user = request.user
            else:
                # 匿名用户使用id=1用户的映射
                try:
                    user = User.objects.get(id=1)
                except User.DoesNotExist:
                    return {'expense': 0, 'assets': 0, 'income': 0, 'total': 0}

            # 统计用户的所有映射记录（包括已关闭的）
            expense_count = Expense.objects.filter(expend=obj, owner=user).count()
            assets_count = Assets.objects.filter(assets=obj, owner=user).count()
            income_count = Income.objects.filter(income=obj, owner=user).count()

            return {
                'expense': expense_count,
                'assets': assets_count,
                'income': income_count,
                'total': expense_count + assets_count + income_count
            }
        except:
            return {'expense': 0, 'assets': 0, 'income': 0, 'total': 0}

    def validate_account(self, value):
        """验证账户路径格式"""
        if not all(part.isidentifier() for part in value.split(':')):
            raise serializers.ValidationError("账户路径必须由字母、数字和下划线组成，用冒号分隔")

        # 验证根账户类型
        root = value.split(':')[0]
        valid_roots = ['Assets', 'Liabilities', 'Equity', 'Income', 'Expenses']
        if root not in valid_roots:
            raise serializers.ValidationError(f"根账户必须是以下之一: {', '.join(valid_roots)}")

        return value


class AccountBatchUpdateSerializer(serializers.Serializer):
    """账户批量更新序列化器"""
    account_ids = serializers.ListField(
        child=serializers.IntegerField(),
        help_text="要更新的账户ID列表"
    )
    action = serializers.ChoiceField(
        choices=['enable', 'disable', 'migrate', 'close'],
        help_text="操作类型"
    )
    target_account_id = serializers.IntegerField(
        required=False,
        help_text="目标账户ID（用于迁移操作）"
    )

    def validate_account_ids(self, value):
        """验证账户ID列表"""
        if not value:
            raise serializers.ValidationError("账户ID列表不能为空")
        return value

    def validate(self, data):
        """验证整体数据"""
        action = data.get('action')
        target_account_id = data.get('target_account_id')

        if action == 'migrate' and not target_account_id:
            raise serializers.ValidationError("迁移操作需要指定目标账户ID")

        return data


class AccountMigrationSerializer(serializers.Serializer):
    """账户迁移序列化器"""
    source_account_id = serializers.IntegerField(help_text="源账户ID")
    target_account_id = serializers.IntegerField(help_text="目标账户ID")
    migrate_mappings = serializers.BooleanField(
        default=True,
        help_text="是否迁移相关映射"
    )
    close_source = serializers.BooleanField(
        default=False,
        help_text="是否关闭源账户"
    )

    def validate_source_account_id(self, value):
        """验证源账户"""
        try:
            account = Account.objects.get(id=value)
            if not account.enable:
                raise serializers.ValidationError("源账户已禁用")
            return value
        except Account.DoesNotExist:
            raise serializers.ValidationError("源账户不存在")

    def validate_target_account_id(self, value):
        """验证目标账户"""
        try:
            account = Account.objects.get(id=value)
            if not account.enable:
                raise serializers.ValidationError("目标账户已禁用")
            return value
        except Account.DoesNotExist:
            raise serializers.ValidationError("目标账户不存在")

    def validate(self, data):
        """验证整体数据"""
        source_id = data.get('source_account_id')
        target_id = data.get('target_account_id')

        if source_id == target_id:
            raise serializers.ValidationError("源账户和目标账户不能相同")

        return data


class AccountDeleteSerializer(serializers.Serializer):
    """账户删除序列化器"""
    migrate_to = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="迁移目标账户ID（可选，无映射时可为空）"
    )

    def validate_migrate_to(self, value):
        """验证迁移目标账户"""
        if value is None:
            return value

        try:
            account = Account.objects.get(id=value)
            if not account.enable:
                raise serializers.ValidationError("目标账户已禁用")
            return value
        except Account.DoesNotExist:
            raise serializers.ValidationError("目标账户不存在")
