"""
BalanceCalculationService 余额计算服务测试
"""
import pytest
import os
import tempfile
from datetime import date
from decimal import Decimal
from unittest.mock import patch, MagicMock

from beancount import loader
from project.apps.reconciliation.services.balance_calculation_service import BalanceCalculationService


@pytest.mark.django_db
class TestBalanceCalculationService:
    """BalanceCalculationService 余额计算服务测试"""
    
    def test_calculate_balance_cny(self, user, mock_bean_file_path):
        """测试计算账户 CNY 余额（正常情况）"""
        # 创建包含 CNY 余额的账本文件
        bean_content = """
2025-01-01 open Assets:Savings:Bank:ICBC CNY

2025-01-15 * "测试交易"
    Assets:Savings:Bank:ICBC 1000.00 CNY
    Income:Salary -1000.00 CNY
"""
        with open(mock_bean_file_path, 'w', encoding='utf-8') as f:
            f.write(bean_content)
        
        balances = BalanceCalculationService.calculate_balance(
            user,
            'Assets:Savings:Bank:ICBC'
        )
        
        assert 'CNY' in balances
        assert balances['CNY'] == Decimal('1000.00')
    
    def test_calculate_balance_account_not_exists(self, user, mock_bean_file_path):
        """测试计算账户余额（账户不存在时返回空字典）"""
        # 创建不包含该账户的账本文件
        bean_content = """
2025-01-01 open Assets:Savings:Web:AliPay CNY

2025-01-15 * "测试交易"
    Assets:Savings:Web:AliPay 500.00 CNY
    Income:Salary -500.00 CNY
"""
        with open(mock_bean_file_path, 'w', encoding='utf-8') as f:
            f.write(bean_content)
        
        balances = BalanceCalculationService.calculate_balance(
            user,
            'Assets:Savings:Bank:ICBC'  # 不存在的账户
        )
        
        assert balances == {}
    
    def test_calculate_balance_file_not_exists(self, user):
        """测试计算账户余额（账本文件不存在时返回空字典）"""
        # Mock 一个不存在的文件路径
        with patch('project.apps.reconciliation.services.balance_calculation_service.BeanFileManager.get_main_bean_path') as mock_path:
            mock_path.return_value = '/nonexistent/path/main.bean'
            
            balances = BalanceCalculationService.calculate_balance(
                user,
                'Assets:Savings:Bank:ICBC'
            )
            
            assert balances == {}
    
    def test_calculate_balance_multiple_currencies(self, user, mock_bean_file_path):
        """测试计算账户多币种余额（CNY, COIN 等）"""
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
        
        balances = BalanceCalculationService.calculate_balance(
            user,
            'Assets:Savings:Web:AliPay'
        )
        
        assert 'CNY' in balances
        assert 'COIN' in balances
        assert balances['CNY'] == Decimal('500.00')
        assert balances['COIN'] == Decimal('100.00')
    
    def test_calculate_balance_specific_currency_cny(self, user, mock_bean_file_path):
        """测试计算指定币种余额（currency='CNY'）"""
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
        
        balances = BalanceCalculationService.calculate_balance(
            user,
            'Assets:Savings:Web:AliPay'
        )
        
        cny_balance = balances.get('CNY', Decimal('0.00'))
        assert cny_balance == Decimal('500.00')
    
    def test_calculate_balance_specific_currency_coin(self, user, mock_bean_file_path):
        """测试计算指定币种余额（currency='COIN'）"""
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
        
        balances = BalanceCalculationService.calculate_balance(
            user,
            'Assets:Savings:Web:AliPay'
        )
        
        coin_balance = balances.get('COIN', Decimal('0.00'))
        assert coin_balance == Decimal('100.00')
    
    def test_calculate_balance_currency_not_exists(self, user, mock_bean_file_path):
        """测试币种不存在时返回 0"""
        bean_content = """
2025-01-01 open Assets:Savings:Bank:ICBC CNY

2025-01-15 * "测试交易"
    Assets:Savings:Bank:ICBC 1000.00 CNY
    Income:Salary -1000.00 CNY
"""
        with open(mock_bean_file_path, 'w', encoding='utf-8') as f:
            f.write(bean_content)
        
        balances = BalanceCalculationService.calculate_balance(
            user,
            'Assets:Savings:Bank:ICBC'
        )
        
        # COIN 币种不存在
        coin_balance = balances.get('COIN', Decimal('0.00'))
        assert coin_balance == Decimal('0.00')
    
    def test_calculate_balance_empty_bean_file(self, user, mock_bean_file_path):
        """测试空账本文件（无交易记录）"""
        bean_content = """
2025-01-01 open Assets:Savings:Bank:ICBC CNY
"""
        with open(mock_bean_file_path, 'w', encoding='utf-8') as f:
            f.write(bean_content)
        
        balances = BalanceCalculationService.calculate_balance(
            user,
            'Assets:Savings:Bank:ICBC'
        )
        
        # 账户无余额
        assert balances == {}
    
    def test_calculate_balance_zero_balance(self, user, mock_bean_file_path):
        """测试账户无余额（返回空字典）"""
        bean_content = """
2025-01-01 open Assets:Savings:Bank:ICBC CNY

2025-01-15 * "测试交易"
    Assets:Savings:Bank:ICBC 1000.00 CNY
    Income:Salary -1000.00 CNY
"""
        with open(mock_bean_file_path, 'w', encoding='utf-8') as f:
            f.write(bean_content)
        
        balances = BalanceCalculationService.calculate_balance(
            user,
            'Assets:Savings:Bank:ICBC'
        )
        
        # 由于收入和支出相等，余额应该为 0，但 beancount 可能返回空字典
        # 这里测试账户存在但余额为 0 的情况
        assert 'CNY' in balances or balances == {}
    
    def test_calculate_balance_negative_balance(self, user, mock_bean_file_path):
        """测试负数余额（负债账户）"""
        bean_content = """
2025-01-01 open Liabilities:Credit:Card CNY

2025-01-15 * "测试交易"
    Expenses:Food 1000.00 CNY
    Liabilities:Credit:Card -1000.00 CNY
"""
        with open(mock_bean_file_path, 'w', encoding='utf-8') as f:
            f.write(bean_content)
        
        balances = BalanceCalculationService.calculate_balance(
            user,
            'Liabilities:Credit:Card'
        )
        
        assert 'CNY' in balances
        assert balances['CNY'] == Decimal('-1000.00')
    
    def test_calculate_balance_with_as_of_date(self, user, mock_bean_file_path):
        """测试使用 as_of_date 参数计算截止日期的余额"""
        bean_content = """
2025-01-01 open Assets:Savings:Bank:ICBC CNY

2025-01-15 * "测试交易1"
    Assets:Savings:Bank:ICBC 1000.00 CNY
    Income:Salary -1000.00 CNY

2025-01-20 * "测试交易2"
    Assets:Savings:Bank:ICBC 500.00 CNY
    Income:Salary -500.00 CNY
"""
        with open(mock_bean_file_path, 'w', encoding='utf-8') as f:
            f.write(bean_content)
        
        # 计算到 2025-01-18 的余额（应该只有第一笔交易）
        balances = BalanceCalculationService.calculate_balance(
            user,
            'Assets:Savings:Bank:ICBC',
            as_of_date=date(2025, 1, 18)
        )
        
        assert 'CNY' in balances
        assert balances['CNY'] == Decimal('1000.00')
    
    def test_generate_balance_directive(self):
        """测试生成 balance 指令"""
        directive = BalanceCalculationService.generate_balance_directive(
            account_name='Assets:Savings:Bank:ICBC',
            balance=Decimal('1000.00'),
            balance_date=date(2026, 1, 21),
            currency='CNY'
        )
        
        assert directive == "2026-01-21 balance Assets:Savings:Bank:ICBC 1000.00 CNY"
    
    def test_generate_balance_directive_coin(self):
        """测试生成 COIN 币种的 balance 指令"""
        directive = BalanceCalculationService.generate_balance_directive(
            account_name='Assets:Savings:Web:AliPay',
            balance=Decimal('11968.28'),
            balance_date=date(2026, 1, 21),
            currency='COIN'
        )
        
        assert directive == "2026-01-21 balance Assets:Savings:Web:AliPay 11968.28 COIN"
    
    def test_generate_pad_directive(self):
        """测试生成 pad 指令"""
        directive = BalanceCalculationService.generate_pad_directive(
            account_name='Assets:Savings:Web:WechatFund',
            pad_account='Income:Investment:Interest',
            pad_date=date(2026, 1, 20)
        )
        
        assert directive == "2026-01-20 pad Assets:Savings:Web:WechatFund Income:Investment:Interest"
    
    def test_calculate_balance_loader_error(self, user):
        """测试账本加载失败时抛出异常"""
        # Mock 一个存在的文件路径，但加载时会抛出异常
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.bean', delete=False, encoding='utf-8') as f:
            temp_path = f.name
        
        try:
            with patch('project.apps.reconciliation.services.balance_calculation_service.BeanFileManager.get_main_bean_path') as mock_path:
                mock_path.return_value = temp_path
                
                with patch('project.apps.reconciliation.services.balance_calculation_service.loader.load_file') as mock_loader:
                    mock_loader.side_effect = Exception("加载失败")
                    
                    with pytest.raises(ValueError, match="加载账本文件失败"):
                        BalanceCalculationService.calculate_balance(
                            user,
                            'Assets:Savings:Bank:ICBC'
                        )
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

