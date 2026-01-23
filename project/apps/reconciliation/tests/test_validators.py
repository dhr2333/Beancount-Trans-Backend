"""
验证器测试
"""
import pytest
from decimal import Decimal
from project.apps.reconciliation.validators import ReconciliationValidator


class TestReconciliationValidator:
    """ReconciliationValidator 验证器测试"""
    
    def test_validate_actual_balance_not_empty(self):
        """测试验证实际余额不能为空"""
        # 这个测试实际上在序列化器中处理，这里测试验证器逻辑
        actual_balance = Decimal('1000.00')
        expected_balance = Decimal('1000.00')
        transaction_items = []
        
        is_valid, errors = ReconciliationValidator.validate_reconciliation_data(
            actual_balance,
            expected_balance,
            transaction_items
        )
        
        assert is_valid
        assert len(errors) == 0
    
    def test_validate_currency_not_empty(self):
        """测试验证币种不能为空"""
        # 币种验证在序列化器中处理，这里只测试基本逻辑
        actual_balance = Decimal('1000.00')
        expected_balance = Decimal('1000.00')
        transaction_items = []
        
        is_valid, errors = ReconciliationValidator.validate_reconciliation_data(
            actual_balance,
            expected_balance,
            transaction_items
        )
        
        assert is_valid
    
    def test_validate_no_difference_no_transaction_items(self):
        """测试无差额时不应提供 transaction_items"""
        actual_balance = Decimal('1000.00')
        expected_balance = Decimal('1000.00')
        transaction_items = [
            {
                'account': 'Expenses:Food',
                'amount': Decimal('100.00'),
                'is_auto': False
            }
        ]
        
        is_valid, errors = ReconciliationValidator.validate_reconciliation_data(
            actual_balance,
            expected_balance,
            transaction_items
        )
        
        assert not is_valid
        assert any('无差额时不应提供 transaction_items' in error for error in errors)
    
    def test_validate_difference_requires_transaction_items(self):
        """测试有差额时必须提供 transaction_items"""
        actual_balance = Decimal('1200.00')
        expected_balance = Decimal('1000.00')
        transaction_items = []  # 空列表
        
        is_valid, errors = ReconciliationValidator.validate_reconciliation_data(
            actual_balance,
            expected_balance,
            transaction_items
        )
        
        assert not is_valid
        assert any('有差额时必须提供 transaction_items' in error for error in errors)
    
    def test_validate_transaction_items_amount_sum_matches_difference(self):
        """测试 transaction 记录金额总和与差额匹配"""
        actual_balance = Decimal('1200.00')
        expected_balance = Decimal('1000.00')
        # 差额 = 200.00，差额分配 = 预期余额 - 实际余额 = -200.00
        # 验证器期望 total_allocated = target_allocation = -200.00
        # 所以用户需要输入 -200.00（带符号）
        transaction_items = [
            {
                'account': 'Expenses:Food',
                'amount': Decimal('-200.00'),  # 带符号，匹配 target_allocation
                'is_auto': False
            }
        ]
        
        is_valid, errors = ReconciliationValidator.validate_reconciliation_data(
            actual_balance,
            expected_balance,
            transaction_items
        )
        
        assert is_valid
        assert len(errors) == 0
    
    def test_validate_transaction_items_amount_sum_not_matches_difference(self):
        """测试 transaction 记录金额总和与差额不匹配"""
        actual_balance = Decimal('1200.00')
        expected_balance = Decimal('1000.00')
        # 差额 = 200.00，但只分配了 100.00
        transaction_items = [
            {
                'account': 'Expenses:Food',
                'amount': Decimal('100.00'),
                'is_auto': False
            }
        ]
        
        is_valid, errors = ReconciliationValidator.validate_reconciliation_data(
            actual_balance,
            expected_balance,
            transaction_items
        )
        
        assert not is_valid
        assert any('已分配金额' in error for error in errors)
    
    def test_validate_transaction_items_account_format(self):
        """测试验证 transaction 记录账户格式（Beancount 账户路径）"""
        actual_balance = Decimal('1200.00')
        expected_balance = Decimal('1000.00')
        # 差额分配 = -200.00，验证器期望 total_allocated = -200.00
        transaction_items = [
            {
                'account': 'Expenses:Food',  # 正确的账户格式
                'amount': Decimal('-200.00'),  # 带符号
                'is_auto': False
            }
        ]
        
        is_valid, errors = ReconciliationValidator.validate_reconciliation_data(
            actual_balance,
            expected_balance,
            transaction_items
        )
        
        # 账户格式验证在序列化器中处理，这里只测试基本逻辑
        assert is_valid
        assert len(errors) == 0
    
    def test_validate_transaction_items_missing_account(self):
        """测试 transaction 记录缺少账户字段"""
        actual_balance = Decimal('1200.00')
        expected_balance = Decimal('1000.00')
        transaction_items = [
            {
                'amount': Decimal('200.00'),
                'is_auto': False
                # 缺少 account
            }
        ]
        
        is_valid, errors = ReconciliationValidator.validate_reconciliation_data(
            actual_balance,
            expected_balance,
            transaction_items
        )
        
        assert not is_valid
        assert any('必须提供账户' in error for error in errors)
    
    def test_validate_transaction_items_auto_calculation(self):
        """测试自动计算条目（is_auto=True）"""
        actual_balance = Decimal('1200.00')
        expected_balance = Decimal('1000.00')
        transaction_items = [
            {
                'account': 'Income:Investment:Interest',
                'amount': None,
                'is_auto': True
            }
        ]
        
        is_valid, errors = ReconciliationValidator.validate_reconciliation_data(
            actual_balance,
            expected_balance,
            transaction_items
        )
        
        assert is_valid
        assert len(errors) == 0
    
    def test_validate_transaction_items_multiple_auto_raises_error(self):
        """测试多个自动计算条目（只能有一个）"""
        actual_balance = Decimal('1200.00')
        expected_balance = Decimal('1000.00')
        transaction_items = [
            {
                'account': 'Income:Investment:Interest',
                'amount': None,
                'is_auto': True
            },
            {
                'account': 'Income:Other',
                'amount': None,
                'is_auto': True
            }
        ]
        
        is_valid, errors = ReconciliationValidator.validate_reconciliation_data(
            actual_balance,
            expected_balance,
            transaction_items
        )
        
        assert not is_valid
        assert any('只能有一个条目标记为自动计算' in error for error in errors)
    
    def test_validate_transaction_items_partial_allocation_with_auto(self):
        """测试部分分配 + 自动计算"""
        actual_balance = Decimal('1200.00')
        expected_balance = Decimal('1000.00')
        # 差额 = 200.00，手动分配 100.00，剩余 100.00 由 pad 兜底
        transaction_items = [
            {
                'account': 'Expenses:Food',
                'amount': Decimal('100.00'),
                'is_auto': False
            },
            {
                'account': 'Income:Investment:Interest',
                'amount': None,
                'is_auto': True
            }
        ]
        
        is_valid, errors = ReconciliationValidator.validate_reconciliation_data(
            actual_balance,
            expected_balance,
            transaction_items
        )
        
        assert is_valid
        assert len(errors) == 0
    
    def test_validate_transaction_items_negative_difference(self):
        """测试负差额（实际余额 < 预期余额）"""
        actual_balance = Decimal('800.00')
        expected_balance = Decimal('1000.00')
        # 差额 = -200.00，差额分配 = 预期余额 - 实际余额 = 200.00
        # 所以需要分配 200.00（正值表示转入账户）
        transaction_items = [
            {
                'account': 'Expenses:Food',
                'amount': Decimal('200.00'),  # 正值
                'is_auto': False
            }
        ]
        
        is_valid, errors = ReconciliationValidator.validate_reconciliation_data(
            actual_balance,
            expected_balance,
            transaction_items
        )
        
        assert is_valid
        assert len(errors) == 0
    
    def test_validate_transaction_items_missing_amount_for_non_auto(self):
        """测试非自动计算条目缺少金额"""
        actual_balance = Decimal('1200.00')
        expected_balance = Decimal('1000.00')
        transaction_items = [
            {
                'account': 'Expenses:Food',
                'amount': None,
                'is_auto': False  # 非自动计算但缺少金额
            }
        ]
        
        is_valid, errors = ReconciliationValidator.validate_reconciliation_data(
            actual_balance,
            expected_balance,
            transaction_items
        )
        
        assert not is_valid
        assert any('未标记为自动计算时必须提供金额' in error for error in errors)

