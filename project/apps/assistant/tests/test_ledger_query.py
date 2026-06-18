import pytest

from project.apps.assistant.services.bql_validator import BQLValidationError
from project.apps.assistant.services.ledger_query import LedgerQueryService


@pytest.mark.django_db
class TestLedgerQueryService:
    def test_ledger_exists(self, user, bean_file):
        service = LedgerQueryService(user)
        assert service.ledger_exists()

    def test_execute_expense_query(self, user, bean_file):
        service = LedgerQueryService(user)
        result = service.execute(
            "SELECT account, sum(position) WHERE account ~ 'Expenses' GROUP BY account"
        )
        assert 'Expenses:Food' in result.result_text
        assert '50.00' in result.result_text or '50' in result.result_text

    def test_reject_invalid_bql(self, user, bean_file):
        service = LedgerQueryService(user)
        with pytest.raises(BQLValidationError):
            service.execute('INSERT INTO foo VALUES (1)')

    def test_list_accounts(self, user, bean_file):
        service = LedgerQueryService(user)
        accounts = service.list_accounts()
        assert 'Expenses:Food' in accounts
        assert 'Assets:Cash' in accounts

    def test_execute_number_filter_query(self, user, bean_file):
        service = LedgerQueryService(user)
        result = service.execute(
            "SELECT date, units(position) WHERE account ~ 'Expenses' AND number > 30"
        )
        assert '50' in result.result_text or '50.00' in result.result_text

    def test_reject_units_position_compare_before_execute(self, user, bean_file):
        service = LedgerQueryService(user)
        with pytest.raises(BQLValidationError, match='units\\(position\\)'):
            service.execute(
                "SELECT date WHERE account ~ 'Expenses' AND units(position) > 100"
            )

    def test_execute_enriches_with_platform_description(
        self, user, bean_file, platform_metadata
    ):
        service = LedgerQueryService(user)
        result = service.execute(
            "SELECT account, sum(position) WHERE account ~ 'Expenses' GROUP BY account"
        )
        assert '餐饮（Expenses:Food）' in result.result_text


ZERO_BALANCE_BEAN = """2024-01-01 open Assets:Savings:Cash CNY
2024-01-01 open Assets:Savings:Web:AliPay CNY
2024-01-01 open Expenses:Food CNY

2024-06-01 * "转入又转出"
  Assets:Savings:Cash  100.00 CNY
  Assets:Savings:Web:AliPay  -100.00 CNY

2024-06-02 * "转回"
  Assets:Savings:Cash  -100.00 CNY
  Assets:Savings:Web:AliPay  100.00 CNY
"""


@pytest.fixture
def zero_balance_bean_file(tmp_path, settings, user, monkeypatch):
    assets_dir = tmp_path / user.username
    assets_dir.mkdir(parents=True)
    main_bean = assets_dir / 'main.bean'
    main_bean.write_text(ZERO_BALANCE_BEAN, encoding='utf-8')
    monkeypatch.setattr(settings, 'ASSETS_BASE_PATH', tmp_path)
    return main_bean


@pytest.mark.django_db
class TestZeroBalanceNormalization:
    def test_zero_balance_shows_normalized_amount(self, user, zero_balance_bean_file):
        service = LedgerQueryService(user)
        result = service.execute(
            "SELECT account, sum(units(position)) "
            "WHERE account ~ '^Assets:Savings:Cash' OR account ~ '^Assets:Savings:Web:AliPay' "
            "GROUP BY account"
        )
        assert '0.00 CNY' in result.result_text
        assert result.result_text.count('0.00 CNY') >= 2
