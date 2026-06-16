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
