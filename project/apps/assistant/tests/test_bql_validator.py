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

    def test_reject_units_position_compare(self):
        with pytest.raises(BQLValidationError, match='units\\(position\\)'):
            validate_bql(
                "SELECT date, units(position) WHERE account ~ 'Expenses' "
                "AND units(position) > 100"
            )

    def test_reject_having_clause(self):
        with pytest.raises(BQLValidationError, match='HAVING'):
            validate_bql(
                "SELECT account, sum(units(position)) WHERE account ~ 'Expenses' "
                "GROUP BY account HAVING sum(units(position)) > 100"
            )

    def test_reject_aggregate_in_where(self):
        with pytest.raises(BQLValidationError, match='聚合'):
            validate_bql(
                "SELECT date WHERE account ~ 'Expenses' AND sum(units(position)) > 0"
            )

    def test_reject_aggregate_in_where_with_group_by(self):
        with pytest.raises(BQLValidationError, match='聚合'):
            validate_bql(
                "SELECT account, sum(units(position)) WHERE account ~ 'Expenses' "
                "AND sum(units(position)) > 0 GROUP BY account"
            )

    def test_allow_order_by_sum_after_group_by(self):
        q = validate_bql(
            "SELECT account, sum(units(position)) WHERE account ~ '^Expenses' "
            "AND year = 2026 AND month = 6 GROUP BY account "
            "ORDER BY sum(units(position)) DESC"
        )
        assert 'ORDER BY sum(units(position)) DESC' in q

    def test_allow_number_compare(self):
        q = validate_bql(
            "SELECT date, units(position) WHERE account ~ 'Expenses' AND number > 100"
        )
        assert 'number > 100' in q

    def test_reject_tags_regex(self):
        with pytest.raises(BQLValidationError, match='IN tags'):
            validate_bql(
                "SELECT date, payee WHERE tags ~ 'Discretionary' AND account ~ 'Expenses'"
            )

    def test_allow_tags_in_operator(self):
        q = validate_bql(
            "SELECT sum(units(position)) WHERE 'Discretionary' IN tags AND account ~ '^Expenses'"
        )
        assert "'Discretionary' IN tags" in q
