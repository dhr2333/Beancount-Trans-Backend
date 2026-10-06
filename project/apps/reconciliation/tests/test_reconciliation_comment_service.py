"""
ReconciliationCommentService 对账注释管理服务测试
"""
import os

import pytest

from project.apps.reconciliation.services.reconciliation_comment_service import ReconciliationCommentService
from project.utils.file import BeanFileManager


@pytest.mark.django_db
class TestReconciliationCommentService:
    """ReconciliationCommentService 对账注释管理服务测试"""

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
