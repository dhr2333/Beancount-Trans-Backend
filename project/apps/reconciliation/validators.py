"""
对账数据验证器

提供对账相关数据的验证逻辑。
"""
from decimal import Decimal
from typing import List, Dict, Tuple


class ReconciliationValidator:
    """对账数据验证器"""
    
    @staticmethod
    def validate_reconciliation_data(
        actual_balance: Decimal,
        expected_balance: Decimal,
        transaction_items: List[Dict]
    ) -> Tuple[bool, List[str]]:
        """
        验证对账数据
        
        Args:
            actual_balance: 实际余额
            expected_balance: 预期余额
            transaction_items: 动态表单条目列表
            
        Returns:
            (is_valid, errors) - 是否有效和错误信息列表
        """
        errors = []
        
        # 1. 计算差额
        difference = actual_balance - expected_balance
        
        # 2. 如果无差额，不需要 transaction_items
        if difference == 0:
            if transaction_items:
                errors.append('无差额时不应提供 transaction_items')
            return len(errors) == 0, errors
        
        # 3. 有差额时必须提供 transaction_items
        if not transaction_items:
            errors.append('有差额时必须提供 transaction_items')
            return False, errors
        
        # 4. 验证每个条目的账户字段
        for i, item in enumerate(transaction_items):
            account_name = item.get('account')
            if not account_name:
                errors.append(f'条目 {i+1} 必须提供账户')
                continue
        
        # 5. 验证金额总和和自动计算逻辑
        auto_item = None
        total_allocated = Decimal('0.00')
        auto_count = 0
        
        for i, item in enumerate(transaction_items):
            if item.get('is_auto'):
                auto_item = item
                auto_count += 1
            else:
                amount = item.get('amount')
                if amount is None:
                    errors.append(f'条目 {i+1} 未标记为自动计算时必须提供金额')
                else:
                    try:
                        amount_decimal = Decimal(str(amount))
                        total_allocated += amount_decimal
                    except (ValueError, TypeError):
                        errors.append(f'条目 {i+1} 的金额格式无效')
        
        # 6. 检查自动计算唯一性
        if auto_count > 1:
            errors.append('只能有一个条目标记为自动计算')
        
        # 7. 验证金额总和
        remaining = difference - total_allocated
        
        if auto_count == 0:
            # 模式A：全部手动填写金额（不需要 pad）
            # 允许小数点误差（0.01）
            if abs(total_allocated - difference) > Decimal('0.01'):
                errors.append(
                    f'已分配金额 {total_allocated} 与差额 {difference} 不匹配（全部手动分配时，金额总和必须等于差额）'
                )
        else:
            # 模式B：有一个自动计算条目（使用 pad）
            # 已分配金额不能大于等于差额绝对值（否则自动计算会为0或负数）
            if total_allocated >= abs(difference):
                errors.append('已分配金额不能大于等于差额绝对值')
        
        # 8. 如果有剩余差额，必须要有 auto_item（用于 pad）
        if abs(remaining) > Decimal('0.01') and auto_count == 0:
            errors.append('有剩余差额时必须提供一个标记为自动计算的条目（用于 pad 兜底）')
        
        return len(errors) == 0, errors


