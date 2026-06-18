from decimal import Decimal

import pytest

from project.apps.assistant.services.reply_number_guard import (
    apply_guard_disclaimer,
    extract_amounts,
    validate_reply_numbers,
)


class _Preview:
    def __init__(self, text: str):
        self.result_preview = text


class TestExtractAmounts:
    def test_extracts_money_and_ignores_year(self):
        amounts = extract_amounts('2024年支出 1,234.56 元，另有 50.00')
        assert Decimal('1234.56') in amounts
        assert Decimal('50.00') in amounts
        assert Decimal('2024') not in amounts

    def test_extracts_negative_amounts(self):
        amounts = extract_amounts('收入 -120.50 CNY')
        assert Decimal('-120.50') in amounts


class TestValidateReplyNumbers:
    def test_passes_when_no_amounts_in_reply(self):
        result = validate_reply_numbers('这是定性分析，无具体金额。', [])
        assert result.ok is True

    def test_fails_when_queries_empty_but_reply_has_amounts(self):
        result = validate_reply_numbers('应收款合计 **5000** 元。', [])
        assert result.ok is False
        assert '未执行 BQL' in result.reason

    def test_passes_when_amount_in_query_result(self):
        queries = [_Preview('account | sum\nAssets:Receivable:Person | 5000.00 CNY\n')]
        result = validate_reply_numbers('个人应收款为 **5000.00** 元。', queries)
        assert result.ok is True

    def test_fails_when_amount_not_in_query_result(self):
        queries = [_Preview('account | sum\nAssets:Receivable:Person | 100.00 CNY\n')]
        result = validate_reply_numbers('应收款合计 **5000** 元。', queries)
        assert result.ok is False

    def test_tolerance_for_rounding(self):
        queries = [_Preview('total | 99.99')]
        result = validate_reply_numbers('约 **100.00** 元', queries, tolerance=Decimal('0.01'))
        assert result.ok is True

    def test_passes_zero_balance_with_normalized_result(self):
        queries = [_Preview('account | sum\nAssets:Savings:Cash  0.00 CNY\n')]
        result = validate_reply_numbers('现金余额为 **0** 元。', queries)
        assert result.ok is True

    def test_passes_zero_balance_with_blank_sum_row(self):
        queries = [_Preview('account           s\nAssets:Savings:Cash\n')]
        result = validate_reply_numbers('支付宝当前余额 **0** 元。', queries)
        assert result.ok is True

    def test_passes_when_reply_uses_abs_of_negative_income(self):
        queries = [_Preview('account | sum\nIncome:Salary | -8000.00 CNY\n')]
        result = validate_reply_numbers('本月工资收入 **8000.00** 元。', queries)
        assert result.ok is True

    def test_fails_when_reply_negates_positive_bql_amount(self):
        queries = [_Preview('account | sum\nIncome:Salary | 500.00 CNY\n')]
        result = validate_reply_numbers('收入冲销 **-500.00** 元。', queries)
        assert result.ok is False

    def test_passes_zero_when_all_queries_empty(self):
        queries = [_Preview('(无结果)')]
        result = validate_reply_numbers('5月餐饮支出为 **0** 元。', queries)
        assert result.ok is True

    def test_passes_qualitative_reply_when_all_queries_empty(self):
        queries = [_Preview('(无结果)')]
        result = validate_reply_numbers('2026年5月无餐饮相关记录。', queries)
        assert result.ok is True

    def test_empty_result_still_rejects_fabricated_amount(self):
        queries = [_Preview('(无结果)')]
        result = validate_reply_numbers('餐饮支出 **500** 元。', queries)
        assert result.ok is False

    def test_passes_zero_for_header_only_sum_result(self):
        queries = [_Preview('s\n-')]
        result = validate_reply_numbers('2026年5月餐饮支出为 **0** 元。', queries)
        assert result.ok is True


class TestExtractAmountsMonth:
    def test_ignores_month_number(self):
        amounts = extract_amounts('2026年5月餐饮支出')
        assert Decimal('2026') not in amounts
        assert Decimal('5') not in amounts


class TestApplyGuardDisclaimer:
    def test_appends_disclaimer_once(self):
        text = apply_guard_disclaimer('原始回答')
        assert '查询详情' in text
        assert apply_guard_disclaimer(text) == text
