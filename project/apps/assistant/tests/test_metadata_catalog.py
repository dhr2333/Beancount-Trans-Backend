import pytest

from project.apps.account.models import Account
from project.apps.assistant.services.metadata_catalog import (
    TAG_DESCRIPTION_MAX_LEN,
    build_path_to_description_map,
    format_catalog_for_llm,
    load_account_catalog,
    load_tag_catalog,
)
from project.apps.tags.models import Tag


@pytest.mark.django_db
class TestMetadataCatalog:
    def test_load_account_catalog(self, platform_metadata, user):
        entries = load_account_catalog(user)
        paths = {e.account for e in entries}
        assert 'Expenses:Food' in paths
        food = next(e for e in entries if e.account == 'Expenses:Food')
        assert food.description == '餐饮'
        assert food.account_type == '支出账户'

    def test_load_tag_catalog(self, platform_metadata, user):
        entries = load_tag_catalog(user)
        assert len(entries) == 1
        assert entries[0].full_path == 'Discretionary'
        assert entries[0].description == '非必要支出'

    def test_build_path_to_description_map(self, platform_metadata, user):
        path_map = build_path_to_description_map(user)
        assert path_map['Expenses:Food'] == '餐饮'
        assert 'Assets:Cash' in path_map

    def test_format_catalog_includes_all_expenses(self, platform_metadata, user):
        Account.objects.create(
            owner=user,
            account='Expenses:Transport',
            description='',
            enable=True,
        )
        text = format_catalog_for_llm(user, ledger_accounts=['Expenses:Food'])
        assert '平台账户目录' in text
        assert 'Expenses:Food → 餐饮' in text
        assert 'Expenses:Transport → （无描述）' in text
        assert '平台标签目录' in text
        assert 'Discretionary → 非必要支出' in text

    def test_format_catalog_includes_non_expense_with_description_or_in_ledger(
        self, platform_metadata, user
    ):
        Account.objects.create(
            owner=user,
            account='Income:Salary',
            description='',
            enable=True,
        )
        text = format_catalog_for_llm(user, ledger_accounts=['Income:Salary'])
        assert 'Income:Salary → （无描述）' in text
        assert 'Assets:Cash → 现金' in text

    def test_tag_description_truncation(self, user):
        long_desc = 'x' * (TAG_DESCRIPTION_MAX_LEN + 10)
        Tag.objects.create(owner=user, name='LongTag', description=long_desc, enable=True)
        text = format_catalog_for_llm(user)
        assert 'LongTag →' in text
        assert '…' in text
        assert long_desc not in text
