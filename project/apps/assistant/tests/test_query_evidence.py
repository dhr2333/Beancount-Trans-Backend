from datetime import date

import pytest

from project.apps.assistant.services.assistant_service import (
    QueryRecord,
    query_record_to_dict,
    query_records_from_dicts,
)
from project.apps.assistant.services.ledger_query import LedgerQueryService
from project.apps.assistant.services.query_evidence import (
    build_query_evidence,
    format_cell,
)


class FakeColumn:
    def __init__(self, name: str):
        self.name = name


class TestFormatCell:
    def test_date_and_amount_like(self):
        assert format_cell(date(2024, 1, 5)) == '2024-01-05'
        assert format_cell('(50.00 CNY)') == '50.00 CNY'

    def test_account_path_map(self):
        assert format_cell('Expenses:Food', path_map={'Expenses:Food': '餐饮'}) == '餐饮（Expenses:Food）'


class TestBuildQueryEvidence:
    def test_detail_rows_preferred_columns(self):
        description = [
            FakeColumn('date'),
            FakeColumn('payee'),
            FakeColumn('narration'),
            FakeColumn('account'),
            FakeColumn('units(position)'),
            FakeColumn('extra'),
        ]
        rows = [
            (date(2024, 1, 5), '午餐', '餐厅', 'Expenses:Food', '50.00 CNY', 'x'),
            (date(2024, 1, 6), '晚餐', '火锅', 'Expenses:Food', '80.00 CNY', 'y'),
        ]
        evidence = build_query_evidence(
            description,
            rows,
            row_count=2,
            truncated=False,
            path_map={'Expenses:Food': '餐饮'},
        )
        assert evidence.summary == '共 2 行'
        assert evidence.columns == ['日期', '收款人', '叙述', '账户', '金额']
        assert evidence.rows[0][0] == '2024-01-05'
        assert evidence.rows[0][3] == '餐饮（Expenses:Food）'
        assert 'extra' not in evidence.columns

    def test_truncates_to_max_rows(self):
        description = [FakeColumn('account'), FakeColumn('sum(units(position))')]
        rows = [(f'Expenses:A{i}', f'{i}.00 CNY') for i in range(10)]
        evidence = build_query_evidence(description, rows, row_count=10, truncated=False)
        assert len(evidence.rows) == 5
        assert evidence.summary == '共 10 行，显示前 5 行'
        assert evidence.truncated is True

    def test_empty_result(self):
        evidence = build_query_evidence(
            [FakeColumn('account')],
            [],
            row_count=0,
            truncated=False,
        )
        assert evidence.summary == '无匹配结果'
        assert evidence.rows == []


class TestQueryRecordEvidenceCompat:
    def test_roundtrip_with_evidence(self):
        record = QueryRecord(
            bql='SELECT 1',
            result_preview='ok',
            fava_path='账本/query/?query_string=SELECT%201',
            evidence={
                'summary': '共 1 行',
                'columns': ['账户', '合计'],
                'rows': [['Expenses:Food', '50.00 CNY']],
                'row_count': 1,
                'truncated': False,
            },
        )
        payload = query_record_to_dict(record)
        restored = query_records_from_dicts([payload])[0]
        assert restored.evidence['summary'] == '共 1 行'
        assert restored.evidence['rows'][0][1] == '50.00 CNY'

    def test_old_queries_without_evidence(self):
        records = query_records_from_dicts([
            {'bql': 'SELECT 1', 'result_preview': 'ok'},
        ])
        assert records[0].evidence is None


@pytest.mark.django_db
class TestLedgerQueryEvidence:
    def test_execute_includes_evidence(self, user, bean_file, platform_metadata):
        service = LedgerQueryService(user)
        result = service.execute(
            "SELECT date, payee, narration, account, units(position) "
            "WHERE account ~ 'Expenses' LIMIT 10"
        )
        assert result.evidence is not None
        assert result.evidence.row_count >= 1
        assert '日期' in result.evidence.columns
        assert any('50' in cell for row in result.evidence.rows for cell in row)
