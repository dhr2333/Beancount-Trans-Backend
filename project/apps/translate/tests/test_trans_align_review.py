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


class TestParseStepNoIgnoreOrphanRefund:
    """关闭默认忽略时，无原单支付宝退款也应进入 parsed_data"""

    def _refund_row(self):
        return {
            'transaction_time': '2026-08-26 12:00:00',
            'transaction_category': '退款',
            'counterparty': '商店',
            'commodity': '退款-商品',
            'transaction_type': '收入',
            'amount': 10.0,
            'payment_method': '余额',
            'transaction_status': '退款成功',
            'notes': '/',
            'bill_identifier': 'alipay',
            'uuid': '2026082623001174561431978102_13180601326082620451502259894',
            'discount': False,
        }

    def _run_parse_step(self, args):
        from project.apps.translate.services.steps import ParseStep

        row = self._refund_row()
        config = MagicMock()
        config.flag = '*'
        config.ai_model = 'BERT'
        user = MagicMock()
        user.id = 1
        context = {
            'owner_id': 1,
            'user': user,
            'config': config,
            'prefilter_bill': [row],
            'args': args,
            'parsed_data': [],
            'status': 'pending',
        }
        parsed = {
            'uuid': row['uuid'],
            'cache_key': row['uuid'],
            'selected_expense_key': None,
            'installment_role': None,
        }
        with patch(
            'project.apps.translate.services.steps.build_ledger_index_for_user',
            return_value={},
        ), patch(
            'project.apps.translate.services.steps.build_raw_payment_index',
            return_value={},
        ), patch(
            'project.apps.translate.services.steps.collect_refund_parent_uuids',
            return_value=set(),
        ), patch(
            'project.apps.translate.services.steps.alipay_is_refund_row',
            return_value=True,
        ), patch(
            'project.apps.translate.services.steps.alipay_parent_uuid',
            return_value='2026082623001174561431978102',
        ), patch(
            'project.apps.translate.services.steps.resolve_alipay_refund_peer',
            return_value=None,
        ), patch(
            'project.apps.translate.services.steps.single_parse_transaction',
            return_value=dict(parsed),
        ), patch(
            'project.apps.translate.services.steps.expand_parsed_entry',
            side_effect=lambda entry, *_a, **_k: [entry],
        ), patch(
            'project.apps.translate.services.steps.assign_transaction_links',
        ), patch(
            'project.apps.translate.services.steps.allocate_unique_cache_key',
            side_effect=lambda key, _seen: key,
        ):
            return ParseStep().execute(context)

    def test_default_skips_orphan_refund(self):
        result = self._run_parse_step({})
        assert result['parsed_data'] == []

    def test_no_ignore_keeps_orphan_refund(self):
        result = self._run_parse_step({'no_ignore': True})
        assert len(result['parsed_data']) == 1
        assert result['parsed_data'][0]['uuid'].startswith('2026082623001174561431978102')
