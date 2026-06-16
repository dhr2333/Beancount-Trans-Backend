import pytest

from project.apps.assistant.services.bql_validator import BQLValidationError, validate_bql


class TestBQLValidator:
    def test_valid_select(self):
        q = validate_bql("SELECT account, sum(position) WHERE account ~ 'Expenses' GROUP BY account")
        assert q.startswith('SELECT')

    def test_reject_empty(self):
        with pytest.raises(BQLValidationError):
            validate_bql('')

    def test_reject_non_select(self):
        with pytest.raises(BQLValidationError):
            validate_bql('DELETE FROM postings')

    def test_reject_multiple_statements(self):
        with pytest.raises(BQLValidationError):
            validate_bql("SELECT 1; SELECT 2")

    def test_reject_forbidden_keyword(self):
        with pytest.raises(BQLValidationError):
            validate_bql('SELECT * FROM postings; DROP TABLE postings')

    def test_strip_trailing_semicolon(self):
        q = validate_bql('SELECT account LIMIT 1;')
        assert not q.endswith(';')
