"""
对账模块的序列化器
"""
from rest_framework import serializers
from decimal import Decimal
from datetime import timedelta
from django.db import models

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
    
    # 账户信息（对账待办）
    account_name = serializers.SerializerMethodField()
    account_type = serializers.SerializerMethodField()
    
    # 文件信息（解析待办）
    file_name = serializers.SerializerMethodField()
    file_id = serializers.SerializerMethodField()
    
    # 缓存过期时间（解析待办）
    expires_at = serializers.SerializerMethodField()
    
    class Meta:
        model = ScheduledTask
        fields = [
            'id', 'task_type', 'task_type_display',
            'scheduled_date', 'completed_date',
            'status', 'status_display',
            'account_name', 'account_type',
            'file_name', 'file_id',
            'expires_at',
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
    
    def get_file_name(self, obj):
        """获取关联文件名（解析待办）"""
        from project.apps.translate.models import ParseFile
        if isinstance(obj.content_object, ParseFile):
            return obj.content_object.file.name
        return None
    
    def get_file_id(self, obj):
        """获取文件ID（解析待办）"""
        from project.apps.translate.models import ParseFile
        if isinstance(obj.content_object, ParseFile):
            return obj.content_object.file_id
        return None
    
    def get_expires_at(self, obj):
        """获取缓存过期时间（解析待办）"""
        if obj.task_type == 'parse_review':
            from project.apps.translate.models import ParseFile
            from project.apps.translate.services.parse_review_service import ParseReviewService
            if isinstance(obj.content_object, ParseFile):
                parse_result = ParseReviewService.get_parse_result(obj.content_object.file_id)
                if parse_result and 'expires_at' in parse_result:
                    return parse_result['expires_at']
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
    date = serializers.DateField(
        required=False,
        allow_null=True,
        help_text="交易日期（仅 is_auto=false 时可指定，不能超过 as_of_date）"
    )
    
    def validate(self, data):
        """验证日期字段规则"""
        is_auto = data.get('is_auto', False)
        item_date = data.get('date')
        
        if is_auto and item_date is not None:
            raise serializers.ValidationError('is_auto=true 的条目不允许指定日期')
        
        return data


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
    is_first_reconciliation = serializers.BooleanField(
        help_text="是否首次对账（True=首次，使用 Equity:Opening-Balances；False=后续，使用 Equity:Adjustments）"
    )
    last_reconciliation_date = serializers.DateField(
        required=False,
        allow_null=True,
        help_text="上一次对账日期（如果存在，transaction_items 的日期必须在此日期之后）"
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
        required=True,
        help_text="对账截止日期（必须由前端提供）"
    )
    
    def validate(self, data):
        """验证对账数据"""
        from .validators import ReconciliationValidator
        from .services import BalanceCalculationService
        from .models import ScheduledTask
        
        # 获取任务和账户信息
        task = self.context.get('task')
        if not task:
            raise serializers.ValidationError('未提供待办任务')
        
        account = task.content_object
        
        # 计算预期余额（使用 as_of_date，必须由前端提供）
        as_of_date = data.get('as_of_date')
        if not as_of_date:
            raise serializers.ValidationError('as_of_date 必须由前端提供')
        
        # 检查同一账户是否已经对账过相同的 as_of_date
        # 不允许同一账户同一天被对账两次（基于 as_of_date）
        existing_reconciliation = ScheduledTask.objects.filter(
            task_type='reconciliation',
            content_type=task.content_type,
            object_id=task.object_id,
            status='completed',
            as_of_date=as_of_date
        ).exclude(id=task.id).exists()
        
        if existing_reconciliation:
            raise serializers.ValidationError(
                f'该账户已有 {as_of_date} 的对账记录，不允许重复对账同一日期'
            )
        
        # 检查提交的 as_of_date 是否大于已完成的 as_of_date
        # 获取该账户已完成的对账记录中最大的 as_of_date
        max_completed_as_of_date = ScheduledTask.objects.filter(
            task_type='reconciliation',
            content_type=task.content_type,
            object_id=task.object_id,
            status='completed',
            as_of_date__isnull=False
        ).exclude(id=task.id).aggregate(
            max_date=models.Max('as_of_date')
        )['max_date']
        
        if max_completed_as_of_date and as_of_date <= max_completed_as_of_date:
            raise serializers.ValidationError(
                f'对账日期 {as_of_date} 不能早于或等于上一次对账日期 {max_completed_as_of_date}，只能对账未来的日期'
            )
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
        
        # 验证 transaction_items 中的账户不能与对账账户相同
        account_errors = []
        reconciliation_account = account.account
        for i, item in enumerate(transaction_items):
            item_account = item.get('account')
            if item_account and item_account == reconciliation_account:
                account_errors.append(f'条目 {i+1} 的账户不能与对账账户相同（{reconciliation_account}）')
        
        if account_errors:
            raise serializers.ValidationError({'transaction_items': account_errors})
        
        # 获取上一次对账日期（最近一次完成的对账任务的 as_of_date）
        from django.contrib.contenttypes.models import ContentType
        from project.apps.account.models import Account
        account_content_type = ContentType.objects.get_for_model(Account)
        last_reconciliation = ScheduledTask.objects.filter(
            task_type='reconciliation',
            content_type=account_content_type,
            object_id=account.id,
            status='completed',
            as_of_date__isnull=False
        ).exclude(id=task.id).order_by('-as_of_date').first()
        
        last_reconciliation_date = last_reconciliation.as_of_date if last_reconciliation else None
        
        # 验证 transaction_items 中的日期
        date_errors = []
        for i, item in enumerate(transaction_items):
            item_date = item.get('date')
            is_auto = item.get('is_auto', False)
            
            if not is_auto and item_date is not None:
                # is_auto=false 的条目，日期不能超过 as_of_date
                if item_date > as_of_date:
                    date_errors.append(f'条目 {i+1} 的日期 {item_date} 不能超过对账截止日期 {as_of_date}')
                
                # 日期不能早于上一次对账日期（如果存在）
                if last_reconciliation_date and item_date <= last_reconciliation_date:
                    date_errors.append(
                        f'条目 {i+1} 的日期 {item_date} 不能早于或等于上一次对账日期 {last_reconciliation_date}（必须在 {last_reconciliation_date + timedelta(days=1)} 或之后）'
                    )
        
        if date_errors:
            raise serializers.ValidationError({'transaction_items': date_errors})
        
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


class ReconciliationDuplicateEntrySerializer(serializers.Serializer):
    """重复条目信息序列化器"""
    type = serializers.CharField(help_text="条目类型（Transaction/Pad/Balance）")
    date = serializers.CharField(help_text="日期")
    account = serializers.CharField(help_text="账户")
    line_numbers = serializers.ListField(
        child=serializers.IntegerField(),
        help_text="行号列表"
    )


class ReconciliationDuplicateSerializer(serializers.Serializer):
    """重复条目检测响应序列化器"""
    has_duplicates = serializers.BooleanField(help_text="是否有重复条目")
    duplicate_count = serializers.IntegerField(help_text="重复条目数量")
    duplicates = ReconciliationDuplicateEntrySerializer(
        many=True,
        help_text="重复条目列表"
    )


class ReconciliationCommentResponseSerializer(serializers.Serializer):
    """注释操作响应序列化器"""
    commented_count = serializers.IntegerField(help_text="注释的行数")
    message = serializers.CharField(help_text="操作消息")
    matched_entries = ReconciliationDuplicateEntrySerializer(
        many=True,
        required=False,
        help_text="匹配的条目列表"
    )


class ReconciliationUncommentResponseSerializer(serializers.Serializer):
    """取消注释响应序列化器"""
    uncommented_count = serializers.IntegerField(help_text="取消注释的行数")
    message = serializers.CharField(help_text="操作消息")


