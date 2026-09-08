"""首页解析对齐：trans 字段、validate-entry、no_ignore 预过滤"""
import pytest
from unittest.mock import MagicMock, patch
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

from project.apps.translate.services.parse.ignore_rules.alipay_rule import alipay_pre_filter
from project.apps.translate.services.parse.ignore_rules.wechat_rule import wechatpay_pre_filter
from project.apps.translate.utils.beancount_validator import BeancountValidator

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(username='trans_align_user', password='pass')


class TestNoIgnorePreFilter:
    def test_alipay_default_ignores_closed(self):
        row = {
            'transaction_status': '交易关闭',
            'commodity': '测试商品',
        }
        assert alipay_pre_filter(row, {}) is True
        assert alipay_pre_filter(row, {'no_ignore': False}) is True

    def test_alipay_no_ignore_keeps_closed(self):
        row = {
            'transaction_status': '交易关闭',
            'commodity': '测试商品',
        }
        assert alipay_pre_filter(row, {'no_ignore': True}) is False

    def test_wechat_default_ignores_full_refund(self):
        row = {'transaction_status': '已全额退款'}
        assert wechatpay_pre_filter(row, {}) is True

    def test_wechat_no_ignore_keeps_full_refund(self):
        row = {'transaction_status': '已全额退款'}
        assert wechatpay_pre_filter(row, {'no_ignore': True}) is False


class TestValidateEntryView:
    def test_missing_param(self, api_client):
        response = api_client.post('/api/translate/validate-entry', {}, format='json')
        assert response.status_code == 400

    def test_valid_entry(self, api_client):
        text = (
            '2025-01-20 * "Shop" "Item"\n'
            '    Expenses:Food  10.00 CNY\n'
            '    Assets:Cash  -10.00 CNY\n'
        )
        response = api_client.post(
            '/api/translate/validate-entry',
            {'edited_formatted': text},
            format='json',
        )
        assert response.status_code == 200
        assert 'validation_warning' not in response.data

    def test_invalid_entry_returns_warning(self, api_client):
        response = api_client.post(
            '/api/translate/validate-entry',
            {'edited_formatted': 'not a valid beancount entry'},
            format='json',
        )
        assert response.status_code == 200
        assert response.data.get('validation_warning')


class TestFormatStepEnrichedFields:
    def test_format_step_includes_review_fields(self):
        from project.apps.translate.services.steps import FormatStep

        config = MagicMock()
        config.flag = '*'
        original_row = {
            'transaction_time': '2025-01-20 10:00:00',
            'transaction_type': '支出',
            'payment_method': '余额',
            'counterparty': '商店',
            'commodity': '商品',
        }
        entry = {
            'date': '2025-01-20',
            'time': '10:00:00',
            'uuid': 'uuid-1',
            'cache_key': 'cache-1',
            'status': 'ALiPay - 交易成功',
            'payee': '商店',
            'note': '商品',
            'tag': None,
            'balance': None,
            'balance_date': '2025-01-21',
            'expense': 'Expenses:Food',
            'expenditure_sign': '',
            'account': 'Assets:Cash',
            'account_sign': '-',
            'amount': '10.00',
            'discount': False,
            'currency': 'CNY',
            'selected_expense_key': '商店',
            'expense_candidates_with_score': [{'key': '商店', 'score': 0.9}],
            'counterparty': '商店',
            'commodity': '商品',
            'installment_role': None,
            'installment_period': None,
            'tag_details': [{'path': 'Food', 'sources': [{'type': 'manual'}]}],
            'original_row': original_row,
        }
        context = {
            'filtered_data': [entry],
            'config': config,
            'formatted_data': [],
            'status': 'pending',
        }

        with patch(
            'project.apps.translate.services.steps.FormatData.format_instance',
            return_value='2025-01-20 * "商店" "商品"\n    Expenses:Food 10.00 CNY\n',
        ):
            result = FormatStep().execute(context)

        assert result['status'] != 'error' or 'formatted_data' in result
        fd = result['formatted_data'][0]
        assert fd['id'] == 'cache-1'
        assert fd['uuid'] == 'uuid-1'
        assert fd['edited_formatted'] == fd['formatted']
        assert fd['tag_details'] == [{'path': 'Food', 'sources': [{'type': 'manual'}]}]
        assert fd['original_row']['payment_method'] == '余额'
        assert fd['payment_method'] == '余额'
        assert fd['transaction_type'] == '支出'
