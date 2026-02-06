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
from .account_currency_service import AccountCurrencyService

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
            as_of_date: 对账截止日期，必须由前端提供
            
        Returns:
            包含生成的指令和下一个待办 ID 的字典
        """
        from project.apps.reconciliation.models import ScheduledTask
        from project.apps.account.models import Account
        
        # 1. 获取账户信息
        account = task.content_object  # Account 对象
        if not isinstance(account, Account):
            raise ValueError("待办任务关联的对象不是 Account 类型")
        
        # 2. 验证 as_of_date 必须由前端提供
        if as_of_date is None:
            raise ValueError("as_of_date 必须由前端提供")
        
        # 3. 计算预期余额（使用 as_of_date）
        balances = BalanceCalculationService.calculate_balance(
            task.content_object.owner, 
            account.account,
            as_of_date=as_of_date
        )
        expected_balance = balances.get(currency, Decimal('0.00'))
        
        # 4. 计算差额
        difference = actual_balance - expected_balance
        
        # 5. 根据 as_of_date 计算指令日期
        # transaction/pad 指令日期 = as_of_date
        # balance 指令日期 = as_of_date + 1 day
        transaction_date = as_of_date
        balance_date = as_of_date + timedelta(days=1)
        
        # 6. 生成指令
        # 指令生成顺序：transaction → pad → balance（按需求要求）
        directives = []
        
        if difference == 0:
            # 无差额：仅生成 balance
            directives.append(
                BalanceCalculationService.generate_balance_directive(
                    account.account, actual_balance, balance_date, currency
                )
            )
        else:
            # 有差额：处理 transaction_items
            # 6.1 处理 transaction 条目（手动添加的）
            if not transaction_items:
                transaction_items = []
            
            auto_item = None
            total_allocated = Decimal('0.00')
            transaction_directives = []
            
            for item in transaction_items:
                if item.get('is_auto'):
                    auto_item = item
                else:
                    # 如果金额为空，说明该账户是要自动分配剩余金额的，不该再为该账户生成 transactions 指令
                    amount = item.get('amount')
                    if amount is None:
                        # 金额为空时，跳过该条目，不生成 transaction 指令
                        continue
                    amount = Decimal(str(amount))
                    total_allocated += amount
                    # 使用条目指定的日期，如果未指定则使用 as_of_date
                    item_date = item.get('date') or transaction_date
                    # 生成 transaction 指令
                    transaction_directives.append(
                        ReconciliationService._generate_transaction_directive(
                            task.content_object.owner, account.account, item['account'], amount, currency, item_date
                        )
                    )
            
            # 6.2 处理自动计算条目或剩余差额
            # 在复式记账中：实际余额 + 差额分配 = 预期余额
            # 所以：差额分配 = 预期余额 - 实际余额 = -difference
            # 剩余差额 = -difference - total_allocated
            remaining = -difference - total_allocated
            
            pad_directive = None
            auto_transaction_directive = None
            if auto_item:
                # 有自动计算条目
                if abs(remaining) == Decimal('0.01'):
                    # 金额为正负 0.01 时，使用 transaction 而不是 pad
                    # 使用 remaining 保留正负号（0.01 或 -0.01）
                    auto_transaction_directive = ReconciliationService._generate_transaction_directive(
                        task.content_object.owner, account.account, auto_item['account'], remaining, currency, transaction_date
                    )
                else:
                    # 其他情况使用 pad 兜底
                    # pad 指令会自动处理剩余差额，无需额外的 transaction 指令
                    pad_directive = BalanceCalculationService.generate_pad_directive(
                        account.account, auto_item['account'], transaction_date
                    )
            
            # 6.3 按顺序组装指令：transaction → pad → balance
            directives.extend(transaction_directives)  # 先添加手动 transaction
            if auto_transaction_directive:
                directives.append(auto_transaction_directive)  # 添加自动计算的 transaction（0.01 情况）
            if pad_directive:
                directives.append(pad_directive)  # 再添加 pad（非 0.01 情况）
            directives.append(
                BalanceCalculationService.generate_balance_directive(
                    account.account, actual_balance, balance_date, currency
                )
            )  # 最后添加 balance
        
        # 7. 写入 .bean 文件
        ReconciliationService._append_directives(
            task.content_object.owner, 
            directives
        )
        
        # 8. 更新待办状态（completed_date 使用实际完成日期，保存 as_of_date）
        today = date.today()
        task.status = 'completed'
        task.completed_date = today
        task.as_of_date = as_of_date  # 保存账本对账日期，用于防止重复对账
        task.save()
        
        # 9. 创建下一个待办
        next_task = None
        if account.reconciliation_cycle_unit and account.reconciliation_cycle_interval:
            try:
                next_date = CycleCalculator.get_next_date(
                    account.reconciliation_cycle_unit,
                    account.reconciliation_cycle_interval,
                    task.scheduled_date  # 基于 scheduled_date，而非 completed_date
                )
                
                # 如果计算出的日期是今天或之前，循环延后直到日期为明天之后
                while next_date <= today:
                    next_date = CycleCalculator.get_next_date(
                        account.reconciliation_cycle_unit,
                        account.reconciliation_cycle_interval,
                        next_date  # 基于计算出的 next_date 再延后一个周期
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
        user,
        from_account: str,
        to_account: str,
        amount: Decimal,
        currency: str,
        transaction_date: date
    ) -> str:
        """生成 transaction 指令
        
        如果目标账户不支持源货币，会自动选择合适的货币并使用 @@ 语法进行转换。
        
        示例（货币相同）：
        2026-01-20 * "Beancount-Trans" "对账调整"
          Expenses:Food 3.00 CNY
          Assets:Savings:Web:WechatFund
        
        示例（货币转换）：
        2026-01-19 * "Beancount-Trans" "对账调整"
          Expenses:Food:Dinner 68.00 CNY @@ 68.00 COIN
          Assets:Savings:Recharge:LiangLiangJiaDao
        
        Args:
            user: 用户对象（用于访问账本文件）
            from_account: 源账户（对账账户）
            to_account: 目标账户
            amount: 金额
            currency: 源货币（对账账户的货币）
            transaction_date: 交易日期
            
        Returns:
            Beancount transaction 指令字符串
        """
        # 获取目标账户的合适货币
        target_currency = AccountCurrencyService.select_currency_for_account(
            user, to_account, currency
        )
        
        # 如果目标货币与源货币相同，使用原有格式
        if target_currency == currency:
            return f'''{transaction_date} * "Beancount-Trans" "对账调整"
    {to_account} {amount} {currency}
    {from_account}'''
        
        # 如果目标货币与源货币不同，使用 @@ 语法进行转换
        # @@ 后面的金额使用绝对值
        return f'''{transaction_date} * "Beancount-Trans" "对账调整"
    {to_account} {amount} {target_currency} @@ {abs(amount)} {currency}
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
            
            for directive in directives:
                f.write(directive)
                f.write('\n')
            f.write('\n')
        
        # 如果是新文件，确保 trans/main.bean 包含它
        if is_new_file:
            BeanFileManager.ensure_reconciliation_bean_included(user)
            logger.info(f"已创建对账文件并添加到 trans/main.bean: {reconciliation_path}")
        
        logger.info(f"已写入 {len(directives)} 条对账指令到 {reconciliation_path}")
