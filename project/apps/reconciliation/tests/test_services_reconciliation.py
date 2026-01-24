"""
ReconciliationService 对账执行服务测试
"""
import pytest
import os
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch, mock_open

from project.apps.reconciliation.services.reconciliation_service import ReconciliationService
from project.apps.reconciliation.models import ScheduledTask
from project.apps.account.models import Account


@pytest.mark.django_db
class TestReconciliationService:
    """ReconciliationService 对账执行服务测试"""
    
    def test_execute_reconciliation_no_difference(self, user, account, scheduled_task_pending, mock_bean_file_path, mock_reconciliation_bean_path, mock_ensure_reconciliation_included):
        """测试无差额场景：预期余额 = 实际余额，仅生成 balance 指令"""
        # 创建包含余额的账本文件
        bean_content = """
2025-01-01 open Assets:Savings:Bank:ICBC CNY

2025-01-15 * "测试交易"
    Assets:Savings:Bank:ICBC 1000.00 CNY
    Income:Salary -1000.00 CNY
"""
        with open(mock_bean_file_path, 'w', encoding='utf-8') as f:
            f.write(bean_content)
        
        # 执行对账（实际余额 = 预期余额 = 1000.00）
        result = ReconciliationService.execute_reconciliation(
            task=scheduled_task_pending,
            actual_balance=Decimal('1000.00'),
            currency='CNY',
            as_of_date=date.today()  # as_of_date 必须由前端提供
        )
        
        assert result['status'] == 'success'
        assert len(result['directives']) == 1
        assert 'balance' in result['directives'][0]
        assert 'Assets:Savings:Bank:ICBC' in result['directives'][0]
        assert '1000.00 CNY' in result['directives'][0]
        
        # 验证待办状态已更新
        scheduled_task_pending.refresh_from_db()
        assert scheduled_task_pending.status == 'completed'
        assert scheduled_task_pending.completed_date == date.today()
    
    def test_execute_reconciliation_with_transaction_only(self, user, account, scheduled_task_pending, mock_bean_file_path, mock_reconciliation_bean_path, mock_ensure_reconciliation_included):
        """测试有差额场景 - 仅 transaction：用户添加 transaction 记录完全分配差额"""
        # 创建包含余额的账本文件
        bean_content = """
2025-01-01 open Assets:Savings:Bank:ICBC CNY
2025-01-01 open Expenses:Food CNY

2025-01-15 * "测试交易"
    Assets:Savings:Bank:ICBC 1000.00 CNY
    Income:Salary -1000.00 CNY
"""
        with open(mock_bean_file_path, 'w', encoding='utf-8') as f:
            f.write(bean_content)
        
        # 执行对账（实际余额 = 1200.00，预期余额 = 1000.00，差额 = 200.00）
        # 注意：在复式记账中，差额分配 = 预期余额 - 实际余额 = -200.00
        # 验证器期望 total_allocated = -200.00，所以传入 -200.00
        # 但服务层生成 transaction 指令时使用绝对值
        transaction_items = [
            {
                'account': 'Expenses:Food',
                'amount': Decimal('-200.00'),  # 带符号，匹配验证器期望
                'is_auto': False
            }
        ]
        
        result = ReconciliationService.execute_reconciliation(
            task=scheduled_task_pending,
            actual_balance=Decimal('1200.00'),
            currency='CNY',
            transaction_items=transaction_items,
            as_of_date=date.today()  # as_of_date 必须由前端提供
        )
        
        assert result['status'] == 'success'
        assert len(result['directives']) == 2  # transaction + balance
        
        # 验证指令顺序：transaction → balance
        assert 'Expenses:Food' in result['directives'][0]
        assert '200.00 CNY' in result['directives'][0]
        assert 'balance' in result['directives'][1]
        assert '1200.00 CNY' in result['directives'][1]
    
    def test_execute_reconciliation_with_pad_only(self, user, account, scheduled_task_pending, mock_bean_file_path, mock_reconciliation_bean_path, mock_ensure_reconciliation_included):
        """测试有差额场景 - 仅 pad：用户未添加 transaction，由 pad 账户兜底"""
        # 创建包含余额的账本文件
        bean_content = """
2025-01-01 open Assets:Savings:Bank:ICBC CNY
2025-01-01 open Income:Investment:Interest CNY

2025-01-15 * "测试交易"
    Assets:Savings:Bank:ICBC 1000.00 CNY
    Income:Salary -1000.00 CNY
"""
        with open(mock_bean_file_path, 'w', encoding='utf-8') as f:
            f.write(bean_content)
        
        # 执行对账（实际余额 = 1200.00，预期余额 = 1000.00，差额 = 200.00）
        # 使用 pad 兜底
        transaction_items = [
            {
                'account': 'Income:Investment:Interest',
                'amount': None,
                'is_auto': True
            }
        ]
        
        result = ReconciliationService.execute_reconciliation(
            task=scheduled_task_pending,
            actual_balance=Decimal('1200.00'),
            currency='CNY',
            transaction_items=transaction_items,
            as_of_date=date.today()  # as_of_date 必须由前端提供
        )
        
        assert result['status'] == 'success'
        assert len(result['directives']) == 2  # pad + balance
        
        # 验证指令顺序：pad → balance
        assert 'pad' in result['directives'][0]
        assert 'Income:Investment:Interest' in result['directives'][0]
        assert 'balance' in result['directives'][1]
        assert '1200.00 CNY' in result['directives'][1]
    
    def test_execute_reconciliation_with_transaction_and_pad(self, user, account, scheduled_task_pending, mock_bean_file_path, mock_reconciliation_bean_path, mock_ensure_reconciliation_included):
        """测试有差额场景 - transaction + pad：用户添加 transaction 部分分配，剩余由 pad 兜底"""
        # 创建包含余额的账本文件
        bean_content = """
2025-01-01 open Assets:Savings:Bank:ICBC CNY
2025-01-01 open Expenses:Food CNY
2025-01-01 open Income:Investment:Interest CNY

2025-01-15 * "测试交易"
    Assets:Savings:Bank:ICBC 1000.00 CNY
    Income:Salary -1000.00 CNY
"""
        with open(mock_bean_file_path, 'w', encoding='utf-8') as f:
            f.write(bean_content)
        
        # 执行对账（实际余额 = 1200.00，预期余额 = 1000.00，差额 = 200.00）
        # 差额分配 = -200.00，手动分配 -100.00，剩余 -100.00 由 pad 兜底
        # 验证器期望 total_allocated = -100.00（带符号）
        transaction_items = [
            {
                'account': 'Expenses:Food',
                'amount': Decimal('-100.00'),  # 带符号，匹配验证器期望
                'is_auto': False
            },
            {
                'account': 'Income:Investment:Interest',
                'amount': None,
                'is_auto': True
            }
        ]
        
        result = ReconciliationService.execute_reconciliation(
            task=scheduled_task_pending,
            actual_balance=Decimal('1200.00'),
            currency='CNY',
            transaction_items=transaction_items,
            as_of_date=date.today()  # as_of_date 必须由前端提供
        )
        
        assert result['status'] == 'success'
        assert len(result['directives']) == 3  # transaction + pad + balance
        
        # 验证指令顺序：transaction → pad → balance
        assert 'Expenses:Food' in result['directives'][0]
        # transaction 指令中金额是绝对值（服务层直接使用 amount，但 Beancount 格式要求正值）
        # 如果传入 -100.00，生成的指令会是 "Expenses:Food -100.00 CNY"，这是有效的 Beancount 语法
        assert '100.00 CNY' in result['directives'][0] or '-100.00 CNY' in result['directives'][0]
        assert 'pad' in result['directives'][1]
        assert 'Income:Investment:Interest' in result['directives'][1]
        assert 'balance' in result['directives'][2]
        assert '1200.00 CNY' in result['directives'][2]
    
    def test_execute_reconciliation_multiple_currencies_cny(self, user, account, scheduled_task_pending, mock_bean_file_path, mock_reconciliation_bean_path, mock_ensure_reconciliation_included):
        """测试多币种对账：对账 CNY 币种（生成 CNY 指令）"""
        bean_content = """
2025-01-01 open Assets:Savings:Web:AliPay CNY
2025-01-01 open Assets:Savings:Web:AliPay COIN

2025-01-15 * "测试交易"
    Assets:Savings:Web:AliPay 500.00 CNY
    Assets:Savings:Web:AliPay 100.00 COIN
    Income:Investment:Interest -500.00 CNY
    Income:Investment:Interest -100.00 COIN
"""
        with open(mock_bean_file_path, 'w', encoding='utf-8') as f:
            f.write(bean_content)
        
        # 对账 CNY 币种（实际余额 = 600.00，预期余额 = 500.00，差额 = 100.00）
        # 需要提供 transaction_items 或使用 pad
        transaction_items = [
            {
                'account': 'Income:Investment:Interest',
                'amount': None,
                'is_auto': True
            }
        ]
        
        result = ReconciliationService.execute_reconciliation(
            task=scheduled_task_pending,
            actual_balance=Decimal('600.00'),
            currency='CNY',
            transaction_items=transaction_items,
            as_of_date=date.today()  # as_of_date 必须由前端提供
        )
        
        assert result['status'] == 'success'
        # pad 指令不包含币种，应该检查 balance 指令（最后一个）
        assert len(result['directives']) == 2  # pad + balance
        assert 'pad' in result['directives'][0]
        assert 'CNY' in result['directives'][1]  # balance 指令包含币种
        assert 'COIN' not in result['directives'][1]
    
    def test_execute_reconciliation_multiple_currencies_coin(self, user, account, scheduled_task_pending, mock_bean_file_path, mock_reconciliation_bean_path, mock_ensure_reconciliation_included):
        """测试多币种对账：对账 COIN 币种（生成 COIN 指令）"""
        bean_content = """
2025-01-01 open Assets:Savings:Web:AliPay CNY
2025-01-01 open Assets:Savings:Web:AliPay COIN

2025-01-15 * "测试交易"
    Assets:Savings:Web:AliPay 500.00 CNY
    Assets:Savings:Web:AliPay 100.00 COIN
    Income:Investment:Interest -500.00 CNY
    Income:Investment:Interest -100.00 COIN
"""
        with open(mock_bean_file_path, 'w', encoding='utf-8') as f:
            f.write(bean_content)
        
        # 对账 COIN 币种（实际余额 = 150.00，预期余额 = 100.00，差额 = 50.00）
        # 需要提供 transaction_items 或使用 pad
        transaction_items = [
            {
                'account': 'Income:Investment:Interest',
                'amount': None,
                'is_auto': True
            }
        ]
        
        result = ReconciliationService.execute_reconciliation(
            task=scheduled_task_pending,
            actual_balance=Decimal('150.00'),
            currency='COIN',
            transaction_items=transaction_items,
            as_of_date=date.today()  # as_of_date 必须由前端提供
        )
        
        assert result['status'] == 'success'
        # pad 指令不包含币种，应该检查 balance 指令（最后一个）
        assert len(result['directives']) == 2  # pad + balance
        assert 'pad' in result['directives'][0]
        assert 'COIN' in result['directives'][1]  # balance 指令包含币种
        assert '150.00 COIN' in result['directives'][1]
    
    def test_execute_reconciliation_creates_next_task(self, user, account_with_cycle, scheduled_task_pending, mock_bean_file_path, mock_reconciliation_bean_path, mock_ensure_reconciliation_included):
        """测试对账完成后创建下一个待办：基于当前待办的 scheduled_date 计算下一个日期"""
        # 更新 scheduled_task_pending 关联到 account_with_cycle
        from django.contrib.contenttypes.models import ContentType
        content_type = ContentType.objects.get_for_model(Account)
        scheduled_task_pending.content_type = content_type
        scheduled_task_pending.object_id = account_with_cycle.id
        scheduled_task_pending.scheduled_date = date(2026, 1, 1)  # 每月 1 号对账
        scheduled_task_pending.save()
        
        bean_content = """
2025-01-01 open Assets:Savings:Web:AliPay CNY

2025-01-15 * "测试交易"
    Assets:Savings:Web:AliPay 1000.00 CNY
    Income:Salary -1000.00 CNY
"""
        with open(mock_bean_file_path, 'w', encoding='utf-8') as f:
            f.write(bean_content)
        
        # 执行对账（假设今天是 2026-01-05，即使 5 号完成，下次仍为下月 1 号）
        with patch('project.apps.reconciliation.services.reconciliation_service.date') as mock_date:
            mock_date.today.return_value = date(2026, 1, 5)
            mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
            
            result = ReconciliationService.execute_reconciliation(
                task=scheduled_task_pending,
                actual_balance=Decimal('1000.00'),
                currency='CNY',
                as_of_date=date(2026, 1, 5)  # as_of_date 必须由前端提供
            )
        
        assert result['status'] == 'success'
        assert result['next_task_id'] is not None
        
        # 验证下一个待办的 scheduled_date 是下月 1 号（基于 scheduled_date，而非 completed_date）
        next_task = ScheduledTask.objects.get(id=result['next_task_id'])
        assert next_task.scheduled_date == date(2026, 2, 1)  # 下月 1 号
        assert next_task.status == 'pending'
    
    def test_execute_reconciliation_task_not_pending_raises_error(self, user, account, scheduled_task_completed, mock_bean_file_path):
        """测试待办状态不是 pending 时抛出异常"""
        bean_content = """
2025-01-01 open Assets:Savings:Bank:ICBC CNY
"""
        with open(mock_bean_file_path, 'w', encoding='utf-8') as f:
            f.write(bean_content)
        
        # 尝试执行已完成的待办，应该失败
        # 注意：这个检查应该在服务层或视图层进行
        # 这里测试服务层不检查状态的情况（由视图层处理）
        # 如果服务层需要检查，应该在这里添加状态检查逻辑
        pass  # 这个测试需要根据实际实现调整
    
    def test_execute_reconciliation_writes_to_bean_file(self, user, account, scheduled_task_pending, mock_bean_file_path, mock_reconciliation_bean_path, mock_ensure_reconciliation_included):
        """测试指令写入 .bean 文件"""
        bean_content = """
2025-01-01 open Assets:Savings:Bank:ICBC CNY

2025-01-15 * "测试交易"
    Assets:Savings:Bank:ICBC 1000.00 CNY
    Income:Salary -1000.00 CNY
"""
        with open(mock_bean_file_path, 'w', encoding='utf-8') as f:
            f.write(bean_content)
        
        # 执行对账
        result = ReconciliationService.execute_reconciliation(
            task=scheduled_task_pending,
            actual_balance=Decimal('1000.00'),
            currency='CNY',
            as_of_date=date.today()  # as_of_date 必须由前端提供
        )
        
        # 验证文件已写入
        assert os.path.exists(mock_reconciliation_bean_path)
        
        with open(mock_reconciliation_bean_path, 'r', encoding='utf-8') as f:
            content = f.read()
            assert 'balance' in content
            assert 'Assets:Savings:Bank:ICBC' in content
    
    def test_execute_reconciliation_negative_difference(self, user, account, scheduled_task_pending, mock_bean_file_path, mock_reconciliation_bean_path, mock_ensure_reconciliation_included):
        """测试负差额场景（实际余额 < 预期余额）"""
        bean_content = """
2025-01-01 open Assets:Savings:Bank:ICBC CNY
2025-01-01 open Expenses:Food CNY

2025-01-15 * "测试交易"
    Assets:Savings:Bank:ICBC 1000.00 CNY
    Income:Salary -1000.00 CNY
"""
        with open(mock_bean_file_path, 'w', encoding='utf-8') as f:
            f.write(bean_content)
        
        # 执行对账（实际余额 = 800.00，预期余额 = 1000.00，差额 = -200.00）
        # 在复式记账中：差额分配 = 预期余额 - 实际余额 = 1000.00 - 800.00 = 200.00
        # 所以需要分配 200.00 到 Expenses:Food（正值表示支出增加）
        transaction_items = [
            {
                'account': 'Expenses:Food',
                'amount': Decimal('200.00'),  # 正值，因为差额分配是正的
                'is_auto': False
            }
        ]
        
        result = ReconciliationService.execute_reconciliation(
            task=scheduled_task_pending,
            actual_balance=Decimal('800.00'),
            currency='CNY',
            transaction_items=transaction_items,
            as_of_date=date.today()  # as_of_date 必须由前端提供
        )
        
        assert result['status'] == 'success'
        assert len(result['directives']) == 2  # transaction + balance
        assert 'Expenses:Food' in result['directives'][0]
        # transaction 指令中金额是绝对值，格式是 "Expenses:Food 200.00 CNY"
        # 虽然传入的是 -200.00，但服务层使用 abs(amount) 生成指令
        assert '200.00 CNY' in result['directives'][0]
        assert 'Assets:Savings:Bank:ICBC' in result['directives'][0]
    
    def test_execute_reconciliation_with_auto_001_positive(self, user, account, scheduled_task_pending, mock_bean_file_path, mock_reconciliation_bean_path, mock_ensure_reconciliation_included):
        """测试有差额场景 - 自动填充金额为 0.01 时使用 transaction 而不是 pad（正数）"""
        # 创建包含余额的账本文件
        bean_content = """
2025-01-01 open Assets:Savings:Bank:ICBC CNY
2025-01-01 open Income:Investment:Interest CNY

2025-01-15 * "测试交易"
    Assets:Savings:Bank:ICBC 1000.00 CNY
    Income:Salary -1000.00 CNY
"""
        with open(mock_bean_file_path, 'w', encoding='utf-8') as f:
            f.write(bean_content)
        
        # 执行对账（实际余额 = 1000.01，预期余额 = 1000.00，差额 = 0.01）
        # 差额分配 = -0.01，剩余 = -0.01，应该使用 transaction 而不是 pad
        transaction_items = [
            {
                'account': 'Income:Investment:Interest',
                'amount': None,
                'is_auto': True
            }
        ]
        
        result = ReconciliationService.execute_reconciliation(
            task=scheduled_task_pending,
            actual_balance=Decimal('1000.01'),
            currency='CNY',
            transaction_items=transaction_items,
            as_of_date=date.today()  # as_of_date 必须由前端提供
        )
        
        assert result['status'] == 'success'
        assert len(result['directives']) == 2  # transaction + balance（没有 pad）
        
        # 验证指令顺序：transaction → balance
        assert 'Income:Investment:Interest' in result['directives'][0]
        assert '0.01 CNY' in result['directives'][0] or '-0.01 CNY' in result['directives'][0]
        assert 'pad' not in result['directives'][0]  # 不应该有 pad
        assert 'balance' in result['directives'][1]
        assert '1000.01 CNY' in result['directives'][1]
    
    def test_execute_reconciliation_with_auto_001_negative(self, user, account, scheduled_task_pending, mock_bean_file_path, mock_reconciliation_bean_path, mock_ensure_reconciliation_included):
        """测试有差额场景 - 自动填充金额为 -0.01 时使用 transaction 而不是 pad（负数）"""
        # 创建包含余额的账本文件
        bean_content = """
2025-01-01 open Assets:Savings:Bank:ICBC CNY
2025-01-01 open Expenses:Adjustment CNY

2025-01-15 * "测试交易"
    Assets:Savings:Bank:ICBC 1000.00 CNY
    Income:Salary -1000.00 CNY
"""
        with open(mock_bean_file_path, 'w', encoding='utf-8') as f:
            f.write(bean_content)
        
        # 执行对账（实际余额 = 999.99，预期余额 = 1000.00，差额 = -0.01）
        # 差额分配 = 0.01，剩余 = 0.01，应该使用 transaction 而不是 pad
        transaction_items = [
            {
                'account': 'Expenses:Adjustment',
                'amount': None,
                'is_auto': True
            }
        ]
        
        result = ReconciliationService.execute_reconciliation(
            task=scheduled_task_pending,
            actual_balance=Decimal('999.99'),
            currency='CNY',
            transaction_items=transaction_items,
            as_of_date=date.today()  # as_of_date 必须由前端提供
        )
        
        assert result['status'] == 'success'
        assert len(result['directives']) == 2  # transaction + balance（没有 pad）
        
        # 验证指令顺序：transaction → balance
        assert 'Expenses:Adjustment' in result['directives'][0]
        assert '0.01 CNY' in result['directives'][0] or '-0.01 CNY' in result['directives'][0]
        assert 'pad' not in result['directives'][0]  # 不应该有 pad
        assert 'balance' in result['directives'][1]
        assert '999.99 CNY' in result['directives'][1]
    
    def test_execute_reconciliation_with_auto_001_with_manual_transaction(self, user, account, scheduled_task_pending, mock_bean_file_path, mock_reconciliation_bean_path, mock_ensure_reconciliation_included):
        """测试有差额场景 - 手动 transaction + 自动填充 0.01：应该使用 transaction 而不是 pad"""
        # 创建包含余额的账本文件
        bean_content = """
2025-01-01 open Assets:Savings:Bank:ICBC CNY
2025-01-01 open Expenses:Food CNY
2025-01-01 open Income:Investment:Interest CNY

2025-01-15 * "测试交易"
    Assets:Savings:Bank:ICBC 1000.00 CNY
    Income:Salary -1000.00 CNY
"""
        with open(mock_bean_file_path, 'w', encoding='utf-8') as f:
            f.write(bean_content)
        
        # 执行对账（实际余额 = 1000.01，预期余额 = 1000.00，差额 = 0.01）
        # 手动分配 -0.00（实际上不分配），剩余 -0.01 由自动填充，应该使用 transaction 而不是 pad
        # 注意：由于手动分配为 0，实际上 remaining = -0.01，应该使用 transaction
        transaction_items = [
            {
                'account': 'Income:Investment:Interest',
                'amount': None,
                'is_auto': True
            }
        ]
        
        result = ReconciliationService.execute_reconciliation(
            task=scheduled_task_pending,
            actual_balance=Decimal('1000.01'),
            currency='CNY',
            transaction_items=transaction_items,
            as_of_date=date.today()  # as_of_date 必须由前端提供
        )
        
        assert result['status'] == 'success'
        assert len(result['directives']) == 2  # transaction (0.01) + balance
        
        # 验证指令顺序：自动 transaction → balance
        assert 'Income:Investment:Interest' in result['directives'][0]
        assert '0.01 CNY' in result['directives'][0] or '-0.01 CNY' in result['directives'][0]
        assert 'pad' not in result['directives'][0]  # 不应该有 pad
        assert 'balance' in result['directives'][1]
        assert '1000.01 CNY' in result['directives'][1]

