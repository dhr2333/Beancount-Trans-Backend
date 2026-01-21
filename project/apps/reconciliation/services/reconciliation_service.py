"""
对账服务

处理对账逻辑，包括差额处理、指令生成、待办状态更新等。
"""
import logging
import os
from decimal import Decimal
from datetime import date, timedelta
from typing import List, Dict, Optional
from django.contrib.contenttypes.models import ContentType

from project.utils.file import BeanFileManager
from .balance_calculation_service import BalanceCalculationService
from .cycle_calculator import CycleCalculator

logger = logging.getLogger(__name__)


class ReconciliationService:
    """对账服务：处理差额逻辑和指令生成"""
    
    @staticmethod
    def execute_reconciliation(
        task,
        actual_balance: Decimal,
        currency: str = 'CNY',
        transaction_items: Optional[List[Dict]] = None,
        as_of_date: Optional[date] = None
    ) -> Dict:
        """
        执行对账的核心逻辑
        
        Args:
            task: ScheduledTask 对象
            actual_balance: 实际余额
            currency: 币种，默认 CNY
            transaction_items: 动态表单数据（用于处理差额）
            as_of_date: 对账截止日期，默认为 None（计算到最新）
            
        Returns:
            包含生成的指令和下一个待办 ID 的字典
        """
        from project.apps.reconciliation.models import ScheduledTask
        from project.apps.account.models import Account
        
        # 1. 获取账户信息
        account = task.content_object  # Account 对象
        if not isinstance(account, Account):
            raise ValueError("待办任务关联的对象不是 Account 类型")
        
        # 2. 计算预期余额（使用 as_of_date）
        today = date.today()
        as_of_date = as_of_date or today  # 默认为今天
        
        balances = BalanceCalculationService.calculate_balance(
            task.content_object.owner, 
            account.account,
            as_of_date=as_of_date
        )
        expected_balance = balances.get(currency, Decimal('0.00'))
        
        # 3. 计算差额
        difference = actual_balance - expected_balance
        
        # 4. 生成指令
        # 指令生成顺序：transaction → pad → balance（按需求要求）
        directives = []
        tomorrow = today + timedelta(days=1)
        
        if difference == 0:
            # 无差额：仅生成 balance
            directives.append(
                BalanceCalculationService.generate_balance_directive(
                    account.account, actual_balance, tomorrow, currency
                )
            )
        else:
            # 有差额：处理 transaction_items
            # 4.1 处理 transaction 条目（手动添加的）
            if not transaction_items:
                transaction_items = []
            
            auto_item = None
            total_allocated = Decimal('0.00')
            transaction_directives = []
            
            for item in transaction_items:
                if item.get('is_auto'):
                    auto_item = item
                else:
                    amount = Decimal(str(item['amount']))
                    total_allocated += amount
                    # 生成 transaction 指令
                    transaction_directives.append(
                        ReconciliationService._generate_transaction_directive(
                            account.account, item['account'], amount, currency, today
                        )
                    )
            
            # 4.2 处理自动计算条目或剩余差额
            remaining = difference - total_allocated
            
            pad_directive = None
            if auto_item:
                # 有自动计算条目
                # 生成 pad 指令
                pad_directive = BalanceCalculationService.generate_pad_directive(
                    account.account, auto_item['account'], today
                )
                # 生成 transaction 指令（自动计算）
                transaction_directives.append(
                    ReconciliationService._generate_transaction_directive(
                        account.account, auto_item['account'], remaining, currency, today
                    )
                )
            elif abs(remaining) > Decimal('0.01'):
                # 没有自动计算，但有剩余差额，不允许这种情况
                raise ValueError(
                    f"有剩余差额 {remaining} 时必须提供一个标记为自动计算的条目（用于 pad 兜底）"
                )
            
            # 4.3 按顺序组装指令：transaction → pad → balance
            directives.extend(transaction_directives)  # 先添加 transaction
            if pad_directive:
                directives.append(pad_directive)  # 再添加 pad
            directives.append(
                BalanceCalculationService.generate_balance_directive(
                    account.account, actual_balance, tomorrow, currency
                )
            )  # 最后添加 balance
        
        # 5. 写入 .bean 文件
        ReconciliationService._append_directives(
            task.content_object.owner, 
            directives
        )
        
        # 6. 更新待办状态
        task.status = 'completed'
        task.completed_date = today
        task.save()
        
        # 7. 创建下一个待办
        next_task = None
        if account.reconciliation_cycle_unit and account.reconciliation_cycle_interval:
            try:
                next_date = CycleCalculator.get_next_date(
                    account.reconciliation_cycle_unit,
                    account.reconciliation_cycle_interval,
                    task.scheduled_date  # 基于 scheduled_date，而非 completed_date
                )
                next_task = ScheduledTask.objects.create(
                    task_type='reconciliation',
                    content_type=ContentType.objects.get_for_model(Account),
                    object_id=account.id,
                    scheduled_date=next_date,
                    status='pending'
                )
            except Exception as e:
                logger.error(f"创建下一个待办失败: {e}")
        
        return {
            'status': 'success',
            'directives': directives,
            'next_task_id': next_task.id if next_task else None
        }
    
    @staticmethod
    def _generate_transaction_directive(
        from_account: str,
        to_account: str,
        amount: Decimal,
        currency: str,
        transaction_date: date
    ) -> str:
        """生成 transaction 指令
        
        示例：
        2026-01-20 * "Beancount-Trans" "对账调整"
          Expenses:Food 3.00 CNY
          Assets:Savings:Web:WechatFund
        """
        return f'''{transaction_date} * "Beancount-Trans" "对账调整"
    {to_account} {amount} {currency}
    {from_account}'''
    
    @staticmethod
    def _append_directives(user, directives: List[str]):
        """将指令追加到 trans/reconciliation.bean 文件
        
        对账指令作为交易记录，统一写入 trans/reconciliation.bean 文件。
        首次创建文件时，会自动添加到 trans/main.bean 的 include 列表中。
        
        Args:
            user: 用户对象
            directives: 指令列表
        """
        reconciliation_path = BeanFileManager.get_reconciliation_bean_path(user)
        
        # 确保 trans 目录存在
        trans_dir = os.path.dirname(reconciliation_path)
        os.makedirs(trans_dir, exist_ok=True)
        
        # 检查文件是否已存在（首次创建）
        is_new_file = not os.path.exists(reconciliation_path)
        
        # 追加指令到文件末尾
        with open(reconciliation_path, 'a', encoding='utf-8') as f:
            if is_new_file:
                # 首次创建时添加文件头注释
                f.write("; Trans directory - Auto-generated includes\n")
                f.write("; This file is automatically generated by the platform\n\n")
            
            f.write('\n')  # 确保从新行开始
            for directive in directives:
                f.write(directive)
                f.write('\n')
            f.write('\n')  # 末尾添加空行
        
        # 如果是新文件，确保 trans/main.bean 包含它
        if is_new_file:
            BeanFileManager.ensure_reconciliation_bean_included(user)
            logger.info(f"已创建对账文件并添加到 trans/main.bean: {reconciliation_path}")
        
        logger.info(f"已写入 {len(directives)} 条对账指令到 {reconciliation_path}")


