"""
对账模块的序列化器
"""
from rest_framework import serializers
from decimal import Decimal

from .models import ScheduledTask


class ScheduledTaskSerializer(serializers.ModelSerializer):
    """ScheduledTask 基础序列化器"""
    task_type_display = serializers.CharField(source='get_task_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = ScheduledTask
        fields = [
            'id', 'task_type', 'task_type_display',
            'content_type', 'object_id',
            'scheduled_date', 'completed_date',
            'status', 'status_display',
            'created', 'modified'
        ]
        read_only_fields = ['id', 'created', 'modified', 'task_type_display', 'status_display']


class ScheduledTaskListSerializer(serializers.ModelSerializer):
    """ScheduledTask 列表序列化器（包含关联对象信息）"""
    task_type_display = serializers.CharField(source='get_task_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    # 账户信息
    account_name = serializers.SerializerMethodField()
    account_type = serializers.SerializerMethodField()
    
    class Meta:
        model = ScheduledTask
        fields = [
            'id', 'task_type', 'task_type_display',
            'scheduled_date', 'completed_date',
            'status', 'status_display',
            'account_name', 'account_type',
            'created', 'modified'
        ]
        read_only_fields = ['id', 'created', 'modified']
    
    def get_account_name(self, obj):
        """获取关联账户名称"""
        from project.apps.account.models import Account
        if isinstance(obj.content_object, Account):
            return obj.content_object.account
        return None
    
    def get_account_type(self, obj):
        """获取账户类型"""
        from project.apps.account.models import Account
        if isinstance(obj.content_object, Account):
            return obj.content_object.get_account_type()
        return None


class ScheduledTaskUpdateSerializer(serializers.ModelSerializer):
    """ScheduledTask 更新序列化器（仅允许修改 scheduled_date）"""
    
    class Meta:
        model = ScheduledTask
        fields = ['scheduled_date']


class TransactionItemSerializer(serializers.Serializer):
    """Transaction 条目序列化器"""
    account = serializers.CharField(max_length=128, help_text="账户路径")
    amount = serializers.DecimalField(
        max_digits=19, 
        decimal_places=2, 
        required=False, 
        allow_null=True,
        help_text="金额（留空时为自动计算）"
    )
    is_auto = serializers.BooleanField(
        default=False,
        help_text="是否为自动计算"
    )


class CurrencyBalanceSerializer(serializers.Serializer):
    """币种余额序列化器"""
    currency = serializers.CharField(
        max_length=10,
        help_text="币种"
    )
    expected_balance = serializers.DecimalField(
        max_digits=19, 
        decimal_places=2,
        help_text="预期余额"
    )


class ReconciliationStartSerializer(serializers.Serializer):
    """开始对账响应序列化器"""
    balances = CurrencyBalanceSerializer(
        many=True,
        help_text="所有有余额的币种列表（仅返回余额不为0的币种）"
    )
    account_name = serializers.CharField(
        max_length=128,
        help_text="账户路径"
    )
    as_of_date = serializers.DateField(
        help_text="截止日期"
    )
    default_currency = serializers.CharField(
        max_length=10,
        required=False,
        allow_null=True,
        help_text="默认币种（如果存在CNY则返回CNY，否则返回第一个币种）"
    )


class ReconciliationExecuteSerializer(serializers.Serializer):
    """执行对账请求序列化器"""
    actual_balance = serializers.DecimalField(
        max_digits=19, 
        decimal_places=2,
        help_text="实际余额"
    )
    currency = serializers.CharField(
        max_length=10,
        default='CNY',
        help_text="币种"
    )
    transaction_items = TransactionItemSerializer(
        many=True, 
        required=False,
        help_text="差额分配条目（有差额时使用）"
    )
    as_of_date = serializers.DateField(
        required=False,
        allow_null=True,
        help_text="对账截止日期（默认为今天）"
    )
    
    def validate(self, data):
        """验证对账数据"""
        from datetime import date
        from .validators import ReconciliationValidator
        from .services import BalanceCalculationService
        
        # 获取任务和账户信息
        task = self.context.get('task')
        if not task:
            raise serializers.ValidationError('未提供待办任务')
        
        account = task.content_object
        
        # 计算预期余额（使用 as_of_date）
        as_of_date = data.get('as_of_date') or date.today()
        balances = BalanceCalculationService.calculate_balance(
            account.owner,
            account.account,
            as_of_date=as_of_date
        )
        currency = data.get('currency', 'CNY')
        expected_balance = balances.get(currency, Decimal('0.00'))
        
        # 验证对账数据
        actual_balance = data['actual_balance']
        transaction_items = data.get('transaction_items', [])
        
        # 转换为字典列表
        transaction_items_dict = [
            {
                'account': item.get('account'),
                'amount': item.get('amount'),
                'is_auto': item.get('is_auto', False)
            }
            for item in transaction_items
        ]
        
        is_valid, errors = ReconciliationValidator.validate_reconciliation_data(
            actual_balance,
            expected_balance,
            transaction_items_dict
        )
        
        if not is_valid:
            raise serializers.ValidationError({'transaction_items': errors})
        
        return data


class ReconciliationExecuteResponseSerializer(serializers.Serializer):
    """执行对账响应序列化器"""
    status = serializers.CharField(help_text="执行状态")
    directives = serializers.ListField(
        child=serializers.CharField(),
        help_text="生成的 Beancount 指令列表"
    )
    next_task_id = serializers.IntegerField(
        allow_null=True,
        help_text="下一个待办任务 ID"
    )


