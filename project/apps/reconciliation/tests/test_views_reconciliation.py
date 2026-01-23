"""
对账执行 API 测试
"""
import pytest
import os
from datetime import date
from decimal import Decimal
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch

from project.apps.reconciliation.models import ScheduledTask
from project.apps.account.models import Account


@pytest.mark.django_db
class TestReconciliationAPI:
    """对账执行 API 测试"""
    
    def test_start_reconciliation_returns_expected_balance(self, user, account, scheduled_task_pending, mock_bean_file_path):
        """测试 POST /api/reconciliation/tasks/{id}/start/ 返回预期余额（多币种）"""
        # 创建包含多币种余额的账本文件
        bean_content = """
2025-01-01 open Assets:Savings:Bank:ICBC CNY
2025-01-01 open Assets:Savings:Bank:ICBC COIN

2025-01-15 * "测试交易"
    Assets:Savings:Bank:ICBC 1000.00 CNY
    Assets:Savings:Bank:ICBC 100.00 COIN
    Income:Salary -1000.00 CNY
    Income:Salary -100.00 COIN
"""
        with open(mock_bean_file_path, 'w', encoding='utf-8') as f:
            f.write(bean_content)
        
        client = APIClient()
        client.force_authenticate(user=user)
        
        response = client.post(f'/api/reconciliation/tasks/{scheduled_task_pending.id}/start/')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'balances' in response.data
        assert len(response.data['balances']) == 2
        assert response.data['account_name'] == account.account
        assert 'default_currency' in response.data
    
    def test_start_reconciliation_task_not_exists_returns_404(self, user):
        """测试待办不存在时返回 404"""
        client = APIClient()
        client.force_authenticate(user=user)
        
        response = client.post('/api/reconciliation/tasks/99999/start/')
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_start_reconciliation_task_not_pending_returns_400(self, user, account, scheduled_task_completed, mock_bean_file_path):
        """测试待办状态不是 pending 时返回 400"""
        bean_content = """
2025-01-01 open Assets:Savings:Bank:ICBC CNY
"""
        with open(mock_bean_file_path, 'w', encoding='utf-8') as f:
            f.write(bean_content)
        
        client = APIClient()
        client.force_authenticate(user=user)
        
        response = client.post(f'/api/reconciliation/tasks/{scheduled_task_completed.id}/start/')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert '已完成或已取消' in str(response.data)
    
    def test_execute_reconciliation_no_difference(self, user, account, scheduled_task_pending, mock_bean_file_path, mock_reconciliation_bean_path, mock_ensure_reconciliation_included):
        """测试 POST /api/reconciliation/tasks/{id}/execute/ 无差额场景"""
        bean_content = """
2025-01-01 open Assets:Savings:Bank:ICBC CNY

2025-01-15 * "测试交易"
    Assets:Savings:Bank:ICBC 1000.00 CNY
    Income:Salary -1000.00 CNY
"""
        with open(mock_bean_file_path, 'w', encoding='utf-8') as f:
            f.write(bean_content)
        
        client = APIClient()
        client.force_authenticate(user=user)
        
        response = client.post(
            f'/api/reconciliation/tasks/{scheduled_task_pending.id}/execute/',
            {
                'actual_balance': '1000.00',
                'currency': 'CNY'
            },
            format='json'
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'success'
        assert len(response.data['directives']) == 1
        assert 'balance' in response.data['directives'][0]
        
        # 验证待办状态已更新
        scheduled_task_pending.refresh_from_db()
        assert scheduled_task_pending.status == 'completed'
    
    def test_execute_reconciliation_with_transaction_only(self, user, account, scheduled_task_pending, mock_bean_file_path, mock_reconciliation_bean_path, mock_ensure_reconciliation_included):
        """测试执行对账 - 有差额（仅 transaction）"""
        bean_content = """
2025-01-01 open Assets:Savings:Bank:ICBC CNY
2025-01-01 open Expenses:Food CNY

2025-01-15 * "测试交易"
    Assets:Savings:Bank:ICBC 1000.00 CNY
    Income:Salary -1000.00 CNY
"""
        with open(mock_bean_file_path, 'w', encoding='utf-8') as f:
            f.write(bean_content)
        
        client = APIClient()
        client.force_authenticate(user=user)
        
        # 差额分配 = -200.00，验证器期望 total_allocated = -200.00（带符号）
        response = client.post(
            f'/api/reconciliation/tasks/{scheduled_task_pending.id}/execute/',
            {
                'actual_balance': '1200.00',
                'currency': 'CNY',
                'transaction_items': [
                    {
                        'account': 'Expenses:Food',
                        'amount': '-200.00',  # 带符号，匹配验证器期望
                        'is_auto': False
                    }
                ]
            },
            format='json'
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'success'
        assert len(response.data['directives']) == 2  # transaction + balance
        assert 'Expenses:Food' in response.data['directives'][0]
    
    def test_execute_reconciliation_with_pad_only(self, user, account, scheduled_task_pending, mock_bean_file_path, mock_reconciliation_bean_path, mock_ensure_reconciliation_included):
        """测试执行对账 - 有差额（仅 pad）"""
        bean_content = """
2025-01-01 open Assets:Savings:Bank:ICBC CNY
2025-01-01 open Income:Investment:Interest CNY

2025-01-15 * "测试交易"
    Assets:Savings:Bank:ICBC 1000.00 CNY
    Income:Salary -1000.00 CNY
"""
        with open(mock_bean_file_path, 'w', encoding='utf-8') as f:
            f.write(bean_content)
        
        client = APIClient()
        client.force_authenticate(user=user)
        
        response = client.post(
            f'/api/reconciliation/tasks/{scheduled_task_pending.id}/execute/',
            {
                'actual_balance': '1200.00',
                'currency': 'CNY',
                'transaction_items': [
                    {
                        'account': 'Income:Investment:Interest',
                        'amount': None,
                        'is_auto': True
                    }
                ]
            },
            format='json'
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'success'
        assert len(response.data['directives']) == 2  # pad + balance
        assert 'pad' in response.data['directives'][0]
    
    def test_execute_reconciliation_with_transaction_and_pad(self, user, account, scheduled_task_pending, mock_bean_file_path, mock_reconciliation_bean_path, mock_ensure_reconciliation_included):
        """测试执行对账 - 有差额（transaction + pad）"""
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
        
        client = APIClient()
        client.force_authenticate(user=user)
        
        # 差额分配 = -200.00，手动分配 -100.00，剩余 -100.00 由 pad 兜底
        # 验证器期望 total_allocated = -100.00（带符号）
        response = client.post(
            f'/api/reconciliation/tasks/{scheduled_task_pending.id}/execute/',
            {
                'actual_balance': '1200.00',
                'currency': 'CNY',
                'transaction_items': [
                    {
                        'account': 'Expenses:Food',
                        'amount': '-100.00',  # 带符号，匹配验证器期望
                        'is_auto': False
                    },
                    {
                        'account': 'Income:Investment:Interest',
                        'amount': None,
                        'is_auto': True
                    }
                ]
            },
            format='json'
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'success'
        assert len(response.data['directives']) == 3  # transaction + pad + balance
        assert 'Expenses:Food' in response.data['directives'][0]
        assert 'pad' in response.data['directives'][1]
    
    def test_execute_reconciliation_multiple_currencies_cny(self, user, account, scheduled_task_pending, mock_bean_file_path, mock_reconciliation_bean_path, mock_ensure_reconciliation_included):
        """测试多币种对账：对账 CNY 币种生成 CNY 指令"""
        bean_content = """
2025-01-01 open Assets:Savings:Web:AliPay CNY
2025-01-01 open Assets:Savings:Web:AliPay COIN
2025-01-01 open Income:Investment:Interest CNY

2025-01-15 * "测试交易"
    Assets:Savings:Web:AliPay 500.00 CNY
    Assets:Savings:Web:AliPay 100.00 COIN
    Income:Investment:Interest -500.00 CNY
    Income:Investment:Interest -100.00 COIN
"""
        with open(mock_bean_file_path, 'w', encoding='utf-8') as f:
            f.write(bean_content)
        
        client = APIClient()
        client.force_authenticate(user=user)
        
        # 差额分配 = -100.00，使用 pad 兜底
        response = client.post(
            f'/api/reconciliation/tasks/{scheduled_task_pending.id}/execute/',
            {
                'actual_balance': '600.00',
                'currency': 'CNY',
                'transaction_items': [
                    {
                        'account': 'Income:Investment:Interest',
                        'amount': None,
                        'is_auto': True
                    }
                ]
            },
            format='json'
        )
        
        assert response.status_code == status.HTTP_200_OK
        # pad 指令不包含币种，应该检查 balance 指令（最后一个）
        assert len(response.data['directives']) == 2  # pad + balance
        assert 'pad' in response.data['directives'][0]
        assert 'CNY' in response.data['directives'][1]  # balance 指令包含币种
        assert 'COIN' not in response.data['directives'][1]
    
    def test_execute_reconciliation_multiple_currencies_coin(self, user, account, scheduled_task_pending, mock_bean_file_path, mock_reconciliation_bean_path, mock_ensure_reconciliation_included):
        """测试多币种对账：对账 COIN 币种生成 COIN 指令"""
        bean_content = """
2025-01-01 open Assets:Savings:Web:AliPay CNY
2025-01-01 open Assets:Savings:Web:AliPay COIN
2025-01-01 open Income:Investment:Interest COIN

2025-01-15 * "测试交易"
    Assets:Savings:Web:AliPay 500.00 CNY
    Assets:Savings:Web:AliPay 100.00 COIN
    Income:Investment:Interest -500.00 CNY
    Income:Investment:Interest -100.00 COIN
"""
        with open(mock_bean_file_path, 'w', encoding='utf-8') as f:
            f.write(bean_content)
        
        client = APIClient()
        client.force_authenticate(user=user)
        
        # 差额分配 = -50.00，使用 pad 兜底
        response = client.post(
            f'/api/reconciliation/tasks/{scheduled_task_pending.id}/execute/',
            {
                'actual_balance': '150.00',
                'currency': 'COIN',
                'transaction_items': [
                    {
                        'account': 'Income:Investment:Interest',
                        'amount': None,
                        'is_auto': True
                    }
                ]
            },
            format='json'
        )
        
        assert response.status_code == status.HTTP_200_OK
        # pad 指令不包含币种，应该检查 balance 指令（最后一个）
        assert len(response.data['directives']) == 2  # pad + balance
        assert 'pad' in response.data['directives'][0]
        assert 'COIN' in response.data['directives'][1]  # balance 指令包含币种
        assert '150.00 COIN' in response.data['directives'][1]
    
    def test_execute_reconciliation_actual_balance_format_error(self, user, account, scheduled_task_pending, mock_bean_file_path):
        """测试实际余额格式错误返回 400"""
        bean_content = """
2025-01-01 open Assets:Savings:Bank:ICBC CNY
"""
        with open(mock_bean_file_path, 'w', encoding='utf-8') as f:
            f.write(bean_content)
        
        client = APIClient()
        client.force_authenticate(user=user)
        
        response = client.post(
            f'/api/reconciliation/tasks/{scheduled_task_pending.id}/execute/',
            {
                'actual_balance': 'invalid',  # 无效格式
                'currency': 'CNY'
            },
            format='json'
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_execute_reconciliation_transaction_amount_mismatch(self, user, account, scheduled_task_pending, mock_bean_file_path):
        """测试 transaction 记录金额总和与差额不匹配返回 400"""
        bean_content = """
2025-01-01 open Assets:Savings:Bank:ICBC CNY
2025-01-01 open Expenses:Food CNY

2025-01-15 * "测试交易"
    Assets:Savings:Bank:ICBC 1000.00 CNY
    Income:Salary -1000.00 CNY
"""
        with open(mock_bean_file_path, 'w', encoding='utf-8') as f:
            f.write(bean_content)
        
        client = APIClient()
        client.force_authenticate(user=user)
        
        # 差额分配 = -200.00，但只分配了 -100.00（不匹配）
        # 验证器期望 total_allocated = -200.00，但只提供了 -100.00
        response = client.post(
            f'/api/reconciliation/tasks/{scheduled_task_pending.id}/execute/',
            {
                'actual_balance': '1200.00',
                'currency': 'CNY',
                'transaction_items': [
                    {
                        'account': 'Expenses:Food',
                        'amount': '-100.00',  # 不匹配，应该是 -200.00
                        'is_auto': False
                    }
                ]
            },
            format='json'
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'transaction_items' in response.data

