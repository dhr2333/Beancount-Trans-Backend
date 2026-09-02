from unittest.mock import patch

import pytest
from django.test import override_settings

from project.apps.assistant.services.assistant_service import (
    QueryRecord,
    query_record_to_dict,
    query_records_from_dicts,
)
from project.apps.assistant.services.fava_url import (
    build_query_fava_links,
    build_query_path,
    get_or_create_fava_instance_uuid,
    infer_report_link,
    parse_fava_time_param,
    read_ledger_title,
    slugify_title,
)
from project.apps.fava_instances.models import FavaInstance


class TestSlugifyTitle:
    def test_chinese_title_matches_fava(self):
        assert slugify_title('戴豪锐的账本') == '戴豪锐的账本'

    def test_ascii_title(self):
        assert slugify_title('My Ledger Book') == 'my-ledger-book'


@pytest.mark.django_db
class TestFavaUrlBuilder:
    @pytest.fixture
    def titled_bean(self, tmp_path, settings, user, monkeypatch):
        assets_dir = tmp_path / user.username
        assets_dir.mkdir(parents=True)
        main_bean = assets_dir / 'main.bean'
        main_bean.write_text(
            'option "title" "戴豪锐的账本"\noption "operating_currency" "CNY"\n',
            encoding='utf-8',
        )
        monkeypatch.setattr(settings, 'ASSETS_BASE_PATH', tmp_path)
        return main_bean

    def test_read_ledger_title_from_main_bean(self, titled_bean, user):
        assert read_ledger_title(user) == '戴豪锐的账本'

    def test_build_query_path_contains_slug_and_query_string(self, titled_bean, user):
        bql = "SELECT sum(units(position)) WHERE account ~ '^Expenses:'"
        path = build_query_path(user, bql)
        assert path.startswith('戴豪锐的账本/query/?')
        assert 'query_string=' in path
        assert 'Expenses' in path

    def test_parse_fava_time_param_year(self):
        assert parse_fava_time_param("SELECT 1 WHERE year = 2026") == '2026'

    def test_infer_income_statement_for_expense_aggregate(self, titled_bean, user):
        bql = (
            "SELECT account, sum(units(position)) WHERE account ~ '^Expenses:' "
            "AND year = 2026 GROUP BY account"
        )
        report = infer_report_link(user, bql)
        assert report is not None
        assert report['name'] == 'income_statement'
        assert report['label'] == '2026 损益表'
        assert 'income_statement/?time=2026' in report['path']

    def test_infer_balance_sheet_for_asset_aggregate(self, titled_bean, user):
        bql = (
            "SELECT account, sum(units(position)) WHERE account ~ '^Assets:' "
            "AND year = 2026 GROUP BY account"
        )
        report = infer_report_link(user, bql)
        assert report is not None
        assert report['name'] == 'balance_sheet'
        assert 'balance_sheet/?time=2026' in report['path']

    def test_no_report_for_payee_detail(self, titled_bean, user):
        bql = (
            "SELECT date, payee, narration, account, units(position) "
            "WHERE payee ~ '山姆' AND year = 2026 LIMIT 10"
        )
        assert infer_report_link(user, bql) is None

    def test_build_query_fava_links_includes_report_when_applicable(self, titled_bean, user):
        bql = (
            "SELECT account, sum(units(position)) WHERE account ~ '^Expenses:' "
            "AND year = 2026 GROUP BY account"
        )
        links = build_query_fava_links(user, bql)
        assert links.fava_path.startswith('戴豪锐的账本/query/?')
        assert links.report is not None
        assert links.report['name'] == 'income_statement'

    def test_get_or_create_fava_instance_without_starting_container(self, user):
        with patch('project.apps.fava_instances.services.fava_manager.FavaContainerManager.ensure_running') as ensure:
            uuid = get_or_create_fava_instance_uuid(user)
            ensure.assert_not_called()
        assert FavaInstance.objects.filter(owner=user).count() == 1
        assert str(FavaInstance.objects.get(owner=user).uuid) == uuid

    @override_settings(FAVA_DEPLOY_MODE='static', FAVA_STATIC_USER_MAP={'assistantuser': 'http://127.0.0.1:5001'})
    def test_static_mode_query_path(self, titled_bean, user):
        bql = 'SELECT 1'
        links = build_query_fava_links(user, bql)
        assert links.fava_path.startswith('戴豪锐的账本/query/?')


class TestQueryRecordCompat:
    def test_query_records_from_dicts_without_fava_fields(self):
        records = query_records_from_dicts([
            {'bql': 'SELECT 1', 'result_preview': 'ok'},
        ])
        assert len(records) == 1
        assert records[0].fava_path == ''
        assert records[0].report is None

    def test_query_record_to_dict_roundtrip(self):
        record = QueryRecord(
            bql='SELECT 1',
            result_preview='ok',
            fava_path='戴豪锐的账本/query/?query_string=SELECT%201',
            report={'name': 'income_statement', 'label': '2026 损益表', 'path': '戴豪锐的账本/income_statement/?time=2026'},
        )
        payload = query_record_to_dict(record)
        assert payload['fava_path'].startswith('戴豪锐的账本/query/')
        assert payload['report']['name'] == 'income_statement'
        restored = query_records_from_dicts([payload])[0]
        assert restored.fava_path == record.fava_path
        assert restored.report == record.report
