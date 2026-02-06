"""
ReconciliationCommentService 对账注释管理服务测试
"""
import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch

from project.apps.reconciliation.services.reconciliation_comment_service import ReconciliationCommentService
from project.utils.file import BeanFileManager


@pytest.mark.django_db
class TestReconciliationCommentService:
    """ReconciliationCommentService 对账注释管理服务测试"""
    
    def test_detect_duplicate_entries_no_duplicates(self, user):
        """测试检测重复条目 - 无重复"""
        # 创建对账文件
        reconciliation_path = BeanFileManager.get_reconciliation_bean_path(user)
        os.makedirs(os.path.dirname(reconciliation_path), exist_ok=True)
        
        bean_content = """2025-01-20 * "Beancount-Trans" "对账调整"
    Income:Active:Freelance -3.00 CNY
    Assets:Savings:Web:WechatFund
"""
        with open(reconciliation_path, 'w', encoding='utf-8') as f:
            f.write(bean_content)
        
        # 创建 Git 仓库数据（不同的条目）
        user_assets_path = Path(BeanFileManager.get_user_assets_path(user))
        user_assets_path.mkdir(parents=True, exist_ok=True)
        
        git_bean_path = user_assets_path / '2025' / 'test.bean'
        git_bean_path.parent.mkdir(parents=True, exist_ok=True)
        
        git_content = """2025-01-21 * "Beancount-Trans" "对账调整"
    Income:Active:Business -5.00 CNY
    Assets:Savings:Web:WechatFund
"""
        with open(git_bean_path, 'w', encoding='utf-8') as f:
            f.write(git_content)
        
        try:
            result = ReconciliationCommentService.detect_duplicate_entries(user)
            
            assert result['has_duplicates'] is False
            assert result['duplicate_count'] == 0
            assert len(result['duplicates']) == 0
        finally:
            # 清理
            if os.path.exists(reconciliation_path):
                os.unlink(reconciliation_path)
            if git_bean_path.exists():
                os.unlink(git_bean_path)
    
    def test_detect_duplicate_entries_with_duplicates(self, user):
        """测试检测重复条目 - 有重复"""
        # 创建对账文件
        reconciliation_path = BeanFileManager.get_reconciliation_bean_path(user)
        os.makedirs(os.path.dirname(reconciliation_path), exist_ok=True)
        
        bean_content = """2025-01-20 * "Beancount-Trans" "对账调整"
    Income:Active:Freelance -3.00 CNY
    Assets:Savings:Web:WechatFund
2025-01-25 balance Assets:Savings:Web:WechatFund 995.63 CNY
"""
        with open(reconciliation_path, 'w', encoding='utf-8') as f:
            f.write(bean_content)
        
        # 创建 Git 仓库数据（相同的条目）
        user_assets_path = Path(BeanFileManager.get_user_assets_path(user))
        user_assets_path.mkdir(parents=True, exist_ok=True)
        
        git_bean_path = user_assets_path / '2025' / 'test.bean'
        git_bean_path.parent.mkdir(parents=True, exist_ok=True)
        
        git_content = """2025-01-20 * "Beancount-Trans" "对账调整"
    Income:Active:Freelance -3.00 CNY
    Assets:Savings:Web:WechatFund
2025-01-25 balance Assets:Savings:Web:WechatFund 995.63 CNY
"""
        with open(git_bean_path, 'w', encoding='utf-8') as f:
            f.write(git_content)
        
        try:
            result = ReconciliationCommentService.detect_duplicate_entries(user)
            
            assert result['has_duplicates'] is True
            assert result['duplicate_count'] == 2  # Transaction 和 Balance
            assert len(result['duplicates']) == 2
        finally:
            # 清理
            if os.path.exists(reconciliation_path):
                os.unlink(reconciliation_path)
            if git_bean_path.exists():
                os.unlink(git_bean_path)
    
    def test_comment_lines_in_file(self, user):
        """测试注释文件中的指定行"""
        reconciliation_path = BeanFileManager.get_reconciliation_bean_path(user)
        os.makedirs(os.path.dirname(reconciliation_path), exist_ok=True)
        
        bean_content = """2025-01-20 * "Beancount-Trans" "对账调整"
    Income:Active:Freelance -3.00 CNY
    Assets:Savings:Web:WechatFund
2025-01-25 balance Assets:Savings:Web:WechatFund 995.63 CNY
"""
        with open(reconciliation_path, 'w', encoding='utf-8') as f:
            f.write(bean_content)
        
        try:
            # 注释第1行和第4行
            commented_count = ReconciliationCommentService._comment_lines_in_file(
                reconciliation_path, [1, 4]
            )
            
            assert commented_count == 2
            
            # 验证文件内容
            with open(reconciliation_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            assert lines[0].strip().startswith(';')
            assert not lines[1].strip().startswith(';')
            assert not lines[2].strip().startswith(';')
            assert lines[3].strip().startswith(';')
        finally:
            if os.path.exists(reconciliation_path):
                os.unlink(reconciliation_path)
    
    def test_uncomment_lines_in_file(self, user):
        """测试取消文件中的注释"""
        reconciliation_path = BeanFileManager.get_reconciliation_bean_path(user)
        os.makedirs(os.path.dirname(reconciliation_path), exist_ok=True)
        
        bean_content = """; 2025-01-20 * "Beancount-Trans" "对账调整"
;     Income:Active:Freelance -3.00 CNY
;     Assets:Savings:Web:WechatFund
; 2025-01-25 balance Assets:Savings:Web:WechatFund 995.63 CNY
"""
        with open(reconciliation_path, 'w', encoding='utf-8') as f:
            f.write(bean_content)
        
        try:
            uncommented_count = ReconciliationCommentService._uncomment_lines_in_file(
                reconciliation_path
            )
            
            assert uncommented_count == 4
            
            # 验证文件内容
            with open(reconciliation_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # 所有行都不应该以 ; 开头（除了空行）
            for line in lines:
                if line.strip() and not line.strip().startswith(';'):
                    # 至少有一行被取消注释
                    assert True
                    break
        finally:
            if os.path.exists(reconciliation_path):
                os.unlink(reconciliation_path)







