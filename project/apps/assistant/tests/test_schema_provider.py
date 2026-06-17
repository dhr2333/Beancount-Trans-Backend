from datetime import date

import pytest

from project.apps.assistant.services.assistant_service import build_system_prompt
from project.apps.assistant.services.bql_reference import build_bql_capability_reference
from project.apps.assistant.services.schema_provider import (
    build_bql_examples,
    get_ledger_context,
)


class TestBuildBqlExamples:
    def test_includes_current_and_last_month(self):
        text = build_bql_examples(date(2026, 6, 16))
        assert 'year = 2026 AND month = 6' in text
        assert 'year = 2026 AND month = 5' in text
        assert '【问题】本月总支出是多少？' in text
        assert '【BQL】' in text
        assert "account ~ '^Expenses'" in text

    def test_january_last_month_is_previous_december(self):
        text = build_bql_examples(date(2026, 1, 15))
        assert 'year = 2026 AND month = 1' in text
        assert 'year = 2025 AND month = 12' in text


    def test_large_expense_uses_number_not_units_compare(self):
        text = build_bql_examples(date(2026, 6, 16))
        assert 'number > 100' in text
        assert 'units(position) >' not in text
        assert 'ORDER BY units(position) DESC' in text


class TestBqlCapabilityReference:
    def test_documents_number_and_forbids_units_compare(self):
        ref = build_bql_capability_reference()
        assert 'number > 100' in ref
        assert '禁止 units(position) > N' in ref
        assert 'beancount.github.io' in ref


class TestBuildSystemPrompt:
    def test_includes_reference_date_and_examples(self):
        prompt = build_system_prompt(date(2026, 6, 16))
        assert '基准日期（今天）: 2026-06-16' in prompt
        assert 'BQL 查询示例' in prompt
        assert '【BQL】' in prompt
        assert 'BQL 能力说明' in prompt
        assert 'number > 100' in prompt


@pytest.mark.django_db
class TestGetLedgerContext:
    def test_includes_bql_examples_and_accounts(self, user, bean_file):
        context = get_ledger_context(user, reference_date=date(2026, 6, 16))
        assert 'BQL 查询示例' in context
        assert '【BQL】' in context
        assert 'year = 2026 AND month = 6' in context
        assert 'Expenses:Food' in context
        assert 'BQL 能力说明' in context
        assert '禁止 units(position) > N' in context

    def test_includes_platform_catalog(self, user, bean_file, platform_metadata):
        context = get_ledger_context(user, reference_date=date(2026, 6, 16))
        assert '平台账户目录' in context
        assert 'Expenses:Food → 餐饮' in context
        assert '平台标签目录' in context
        assert 'Discretionary → 非必要支出' in context
        assert '账本实际出现的账户' in context
