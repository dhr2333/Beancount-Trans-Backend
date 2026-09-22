"""Copilot 自然语言记账（record_transaction）助手侧测试。"""

from datetime import date
from unittest.mock import MagicMock

import pytest
from django.test import override_settings

from project.apps.assistant.services.assistant_service import (
    AssistantService,
    build_system_prompt,
    build_tools,
    format_bookkeeping_result,
)

CREATE_ENTRIES_PATH = (
    'project.apps.translate.services.copilot_bookkeeping_service.'
    'CopilotBookkeepingService.create_entries'
)

ENTRY_FIELDS = [
    'type',
    'date',
    'amount',
    'narration',
    'payee',
    'account',
    'payment_account',
    'from_account',
    'to_account',
    'tags',
    'currency',
]

SUCCESS_RESULT = {
    'ok': True,
    'created': [
        {
            'uuid': 'uuid-1',
            'type': 'expense',
            'date': '2026-06-16',
            'amount': '35.50',
            'currency': 'CNY',
            'narration': '午餐',
            'account': 'Expenses:Food',
            'counterparty_account': 'Assets:Cash',
        },
        {
            'uuid': 'uuid-2',
            'type': 'transfer',
            'date': '2026-06-16',
            'amount': '100.00',
            'currency': 'CNY',
            'narration': '转入储蓄',
            'account': 'Assets:Savings',
            'counterparty_account': 'Assets:Cash',
        },
    ],
    'duplicates': [
        {
            'type': 'expense',
            'date': '2026-06-15',
            'amount': '12.00',
            'narration': '打车',
            'reason': '与待审核队列中已有条目重复',
        },
    ],
    'errors': [
        {'index': 2, 'error': '账户不存在'},
    ],
    'pending_total': 3,
}


def _record_transaction_tool(*, insight_mode: bool = False) -> dict:
    tools = build_tools(insight_mode=insight_mode)
    return next(
        t for t in tools if t['function']['name'] == 'record_transaction'
    )


@pytest.mark.django_db
class TestRecordTransactionSchema:
    def test_build_tools_includes_record_transaction(self):
        names = [t['function']['name'] for t in build_tools()]
        assert 'record_transaction' in names
        assert set(names) == {'get_ledger_context', 'run_bql', 'record_transaction'}

    def test_record_transaction_schema_fields(self):
        tool = _record_transaction_tool()
        assert tool['type'] == 'function'
        assert tool['function']['name'] == 'record_transaction'

        params = tool['function']['parameters']
        assert params['type'] == 'object'
        assert params['required'] == ['entries']

        entries = params['properties']['entries']
        assert entries['type'] == 'array'

        items = entries['items']
        assert items['type'] == 'object'
        assert items['required'] == ['type', 'date', 'amount', 'narration']

        props = items['properties']
        for field in ENTRY_FIELDS:
            assert field in props

        assert props['type']['enum'] == ['expense', 'income', 'transfer']
        assert props['date']['type'] == 'string'
        assert props['amount']['type'] == 'number'
        assert props['narration']['type'] == 'string'
        assert props['tags']['type'] == 'array'
        assert props['tags']['items'] == {'type': 'string'}

    def test_record_transaction_description_contract(self):
        desc = _record_transaction_tool()['function']['description']
        assert '记账意图' in desc
        assert 'get_ledger_context' in desc
        assert '禁止编造' in desc
        assert '条目审核' in desc
        assert 'collect.bean' in desc

    @override_settings(COPILOT_BOOKKEEPING_MAX_ENTRIES=4)
    def test_record_transaction_description_reflects_max_entries(self):
        desc = _record_transaction_tool()['function']['description']
        assert '4' in desc
        assert '最多 4 条' in desc

    def test_record_transaction_present_in_insight_mode(self):
        tool = _record_transaction_tool(insight_mode=True)
        assert tool['function']['parameters']['required'] == ['entries']
        assert tool['function']['parameters']['properties']['entries']['type'] == 'array'


class TestFormatBookkeepingResult:
    def test_success_result_includes_all_sections(self):
        text = format_bookkeeping_result(SUCCESS_RESULT)

        assert '已生成 2 条待审核条目' in text
        assert '2026-06-16' in text
        assert '午餐' in text
        assert '35.50' in text
        assert '支出' in text
        assert 'Expenses:Food ← Assets:Cash' in text
        assert '转账' in text
        assert 'Assets:Savings → Assets:Cash' in text

        assert '疑似重复，已跳过 1 条' in text
        assert '打车' in text
        assert '与待审核队列中已有条目重复' in text

        assert '校验失败 1 条' in text
        assert '第 2 条：账户不存在' in text

        assert '待审核条目共 3 条' in text
        assert 'collect.bean' in text
        assert '条目审核' in text

    def test_ok_false_with_errors_gives_explicit_reason(self):
        result = {
            'ok': False,
            'created': [],
            'duplicates': [],
            'errors': [{'index': 1, 'error': '金额非法'}],
            'pending_total': 0,
        }
        text = format_bookkeeping_result(result)

        assert '金额非法' in text
        assert '第 1 条：金额非法' in text
        assert '没有条目被写入' in text
        assert 'collect.bean' in text

    def test_ok_false_without_errors_gives_clear_reason(self):
        result = {
            'ok': False,
            'created': [],
            'duplicates': [],
            'errors': [],
            'pending_total': 0,
        }
        text = format_bookkeeping_result(result)

        assert '记账未成功：没有可处理的条目。' in text
        assert '待审核条目共 0 条' in text
        assert 'collect.bean' in text


@pytest.mark.django_db
class TestDispatchRecordTransaction:
    def test_dispatch_success_returns_readable_text(self, user, monkeypatch):
        mock_create = MagicMock(return_value=SUCCESS_RESULT)
        monkeypatch.setattr(CREATE_ENTRIES_PATH, mock_create)

        service = AssistantService(user)
        entries = [{'type': 'expense', 'date': '2026-06-16', 'amount': 35.5, 'narration': '午餐'}]
        text = service._dispatch_tool('record_transaction', {'entries': entries}, [])

        mock_create.assert_called_once()
        assert mock_create.call_args.args == (user, entries)
        assert '已生成 2 条待审核条目' in text
        assert '午餐' in text
        assert '待审核条目共 3 条' in text
        assert 'collect.bean' in text

    def test_dispatch_service_exception_returns_failure_text(self, user, monkeypatch):
        def _boom(_user, _entries):
            raise RuntimeError('暂存写入失败')

        monkeypatch.setattr(CREATE_ENTRIES_PATH, _boom)

        service = AssistantService(user)
        text = service._dispatch_tool(
            'record_transaction',
            {'entries': [{'type': 'expense'}]},
            [],
        )

        assert text.startswith('记账失败:')
        assert '暂存写入失败' in text

    @pytest.mark.parametrize(
        'arguments',
        [
            {},
            {'entries': 'expense'},
            {'entries': []},
            {'entries': None},
        ],
    )
    def test_dispatch_invalid_entries_does_not_call_service(
        self, user, monkeypatch, arguments,
    ):
        mock_create = MagicMock()
        monkeypatch.setattr(CREATE_ENTRIES_PATH, mock_create)

        service = AssistantService(user)
        text = service._dispatch_tool('record_transaction', arguments, [])

        assert text.startswith('记账失败:')
        assert 'entries 必须是非空数组' in text
        mock_create.assert_not_called()


@pytest.mark.django_db
class TestBookkeepingSystemPrompt:
    def test_prompt_mentions_bookkeeping_tool_and_flow(self):
        prompt = build_system_prompt(date(2026, 6, 16))

        assert 'record_transaction' in prompt
        assert 'collect.bean' in prompt
        assert '条目审核' in prompt
        assert 'get_ledger_context' in prompt
        assert '禁止编造' in prompt

    @pytest.mark.parametrize('insight_mode', [False, True])
    def test_prompt_has_no_unrendered_placeholders(self, insight_mode):
        prompt = build_system_prompt(date(2026, 6, 16), insight_mode=insight_mode)

        assert '{' not in prompt
        assert '}' not in prompt
        assert '{reference_date_context}' not in prompt
        assert '{bql_capability_reference}' not in prompt
        assert '{bql_examples}' not in prompt
        assert '{max_bql_runs}' not in prompt
