"""
EntryMatcher 条目匹配服务测试
"""
import pytest
import tempfile
import os
from datetime import date
from decimal import Decimal

from beancount import loader
from beancount.core.data import Transaction, Pad, Balance

from project.apps.reconciliation.services.entry_matcher import EntryMatcher


@pytest.mark.django_db
class TestEntryMatcher:
    """EntryMatcher 条目匹配服务测试"""
    
    def test_normalize_transaction(self):
        """测试 Transaction 条目标准化"""
        # 创建测试 Transaction
        bean_content = """2025-01-20 * "Beancount-Trans" "对账调整"
    Income:Active:Freelance -3.00 CNY
    Assets:Savings:Web:WechatFund
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.bean', delete=False) as f:
            f.write(bean_content)
            temp_path = f.name
        
        try:
            entries, errors, options = loader.load_file(temp_path)
            transaction = entries[0]
            
            normalized = EntryMatcher.normalize_transaction(transaction)
            
            assert normalized['type'] == 'Transaction'
            assert normalized['date'] == date(2025, 1, 20)
            assert normalized['payee'] == 'Beancount-Trans'
            assert normalized['narration'] == '对账调整'
            assert len(normalized['postings']) == 2
            assert normalized['postings'][0]['account'] == 'Income:Active:Freelance'
            assert normalized['postings'][0]['amount'] == Decimal('-3.00')
            assert normalized['postings'][0]['currency'] == 'CNY'
        finally:
            os.unlink(temp_path)
    
    def test_normalize_pad(self):
        """测试 Pad 条目标准化"""
        bean_content = """2025-01-22 pad Assets:Savings:Web:WechatFund Income:Active:Freelance
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.bean', delete=False) as f:
            f.write(bean_content)
            temp_path = f.name
        
        try:
            entries, errors, options = loader.load_file(temp_path)
            pad = entries[0]
            
            normalized = EntryMatcher.normalize_pad(pad)
            
            assert normalized['type'] == 'Pad'
            assert normalized['date'] == date(2025, 1, 22)
            assert normalized['account'] == 'Assets:Savings:Web:WechatFund'
            assert normalized['source_account'] == 'Income:Active:Freelance'
        finally:
            os.unlink(temp_path)
    
    def test_normalize_balance(self):
        """测试 Balance 条目标准化"""
        bean_content = """2025-01-25 balance Assets:Savings:Web:WechatFund 995.63 CNY
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.bean', delete=False) as f:
            f.write(bean_content)
            temp_path = f.name
        
        try:
            entries, errors, options = loader.load_file(temp_path)
            balance = entries[0]
            
            normalized = EntryMatcher.normalize_balance(balance)
            
            assert normalized['type'] == 'Balance'
            assert normalized['date'] == date(2025, 1, 25)
            assert normalized['account'] == 'Assets:Savings:Web:WechatFund'
            assert normalized['amount'] == Decimal('995.63')
            assert normalized['currency'] == 'CNY'
        finally:
            os.unlink(temp_path)
    
    def test_match_transaction_same(self):
        """测试匹配相同的 Transaction 条目"""
        bean_content1 = """2025-01-20 * "Beancount-Trans" "对账调整"
    Income:Active:Freelance -3.00 CNY
    Assets:Savings:Web:WechatFund
"""
        bean_content2 = """2025-01-20 * "Beancount-Trans" "对账调整"
    Income:Active:Freelance  -3.00 CNY
    Assets:Savings:Web:WechatFund
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.bean', delete=False) as f1:
            f1.write(bean_content1)
            temp_path1 = f1.name
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.bean', delete=False) as f2:
            f2.write(bean_content2)
            temp_path2 = f2.name
        
        try:
            entries1, _, _ = loader.load_file(temp_path1)
            entries2, _, _ = loader.load_file(temp_path2)
            
            entry1 = EntryMatcher.normalize_transaction(entries1[0])
            entry2 = EntryMatcher.normalize_transaction(entries2[0])
            
            assert EntryMatcher.match_transaction(entry1, entry2) is True
        finally:
            os.unlink(temp_path1)
            os.unlink(temp_path2)
    
    def test_match_transaction_different_date(self):
        """测试匹配不同日期的 Transaction 条目"""
        bean_content1 = """2025-01-20 * "Beancount-Trans" "对账调整"
    Income:Active:Freelance -3.00 CNY
    Assets:Savings:Web:WechatFund
"""
        bean_content2 = """2025-01-21 * "Beancount-Trans" "对账调整"
    Income:Active:Freelance -3.00 CNY
    Assets:Savings:Web:WechatFund
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.bean', delete=False) as f1:
            f1.write(bean_content1)
            temp_path1 = f1.name
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.bean', delete=False) as f2:
            f2.write(bean_content2)
            temp_path2 = f2.name
        
        try:
            entries1, _, _ = loader.load_file(temp_path1)
            entries2, _, _ = loader.load_file(temp_path2)
            
            entry1 = EntryMatcher.normalize_transaction(entries1[0])
            entry2 = EntryMatcher.normalize_transaction(entries2[0])
            
            assert EntryMatcher.match_transaction(entry1, entry2) is False
        finally:
            os.unlink(temp_path1)
            os.unlink(temp_path2)
    
    def test_match_balance_same(self):
        """测试匹配相同的 Balance 条目"""
        bean_content1 = """2025-01-25 balance Assets:Savings:Web:WechatFund 995.63 CNY
"""
        bean_content2 = """2025-01-25 balance Assets:Savings:Web:WechatFund  995.63 CNY
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.bean', delete=False) as f1:
            f1.write(bean_content1)
            temp_path1 = f1.name
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.bean', delete=False) as f2:
            f2.write(bean_content2)
            temp_path2 = f2.name
        
        try:
            entries1, _, _ = loader.load_file(temp_path1)
            entries2, _, _ = loader.load_file(temp_path2)
            
            entry1 = EntryMatcher.normalize_balance(entries1[0])
            entry2 = EntryMatcher.normalize_balance(entries2[0])
            
            assert EntryMatcher.match_balance(entry1, entry2) is True
        finally:
            os.unlink(temp_path1)
            os.unlink(temp_path2)
    
    def test_match_entry_lists(self):
        """测试匹配两组条目列表"""
        bean_content1 = """2025-01-20 * "Beancount-Trans" "对账调整"
    Income:Active:Freelance -3.00 CNY
    Assets:Savings:Web:WechatFund
2025-01-25 balance Assets:Savings:Web:WechatFund 995.63 CNY
"""
        bean_content2 = """2025-01-20 * "Beancount-Trans" "对账调整"
    Income:Active:Freelance -3.00 CNY
    Assets:Savings:Web:WechatFund
2025-01-25 balance Assets:Savings:Web:WechatFund 995.63 CNY
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.bean', delete=False) as f1:
            f1.write(bean_content1)
            temp_path1 = f1.name
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.bean', delete=False) as f2:
            f2.write(bean_content2)
            temp_path2 = f2.name
        
        try:
            entries1 = EntryMatcher.parse_bean_file(temp_path1)
            entries2 = EntryMatcher.parse_bean_file(temp_path2)
            
            matched = EntryMatcher.match_entry_lists(entries1, entries2)
            
            assert len(matched) == 2  # Transaction 和 Balance 都匹配
        finally:
            os.unlink(temp_path1)
            os.unlink(temp_path2)



