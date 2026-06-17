from datetime import date

import pytest

from project.apps.assistant.services.assistant_service import build_system_prompt
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


class TestBuildSystemPrompt:
    def test_includes_reference_date_and_examples(self):
        prompt = build_system_prompt(date(2026, 6, 16))
        assert '基准日期（今天）: 2026-06-16' in prompt
        assert 'BQL 查询示例' in prompt
        assert '【BQL】' in prompt
        assert '优先模仿下方示例结构' in prompt


@pytest.mark.django_db
class TestGetLedgerContext:
    def test_includes_bql_examples_and_accounts(self, user, bean_file):
        context = get_ledger_context(user, reference_date=date(2026, 6, 16))
        assert 'BQL 查询示例' in context
        assert '【BQL】' in context
        assert 'year = 2026 AND month = 6' in context
        assert 'Expenses:Food' in context
        assert '不要写 FROM 子句' in context
