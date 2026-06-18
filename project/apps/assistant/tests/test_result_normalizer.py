from project.apps.assistant.services.result_normalizer import normalize_zero_balance_sums


class TestNormalizeZeroBalanceSums:
    def test_fills_blank_sum_rows(self):
        text = (
            'account           s\n'
            '-------------------------  -\n'
            'Assets:Savings:Cash\n'
            'Assets:Savings:Web:AliPay   '
        )
        bql = "SELECT account, sum(units(position)) WHERE account ~ '^Assets' GROUP BY account"
        result = normalize_zero_balance_sums(text, bql, 'CNY')
        assert 'Assets:Savings:Cash  0.00 CNY' in result
        assert 'Assets:Savings:Web:AliPay  0.00 CNY' in result

    def test_preserves_nonzero_rows(self):
        text = (
            'account            sum(units\n'
            '--------------------------  ---------\n'
            'Assets:Savings:Web:AliFund   7.94 CNY\n'
            'Assets:Savings:Cash\n'
        )
        bql = "SELECT account, sum(units(position)) GROUP BY account"
        result = normalize_zero_balance_sums(text, bql, 'CNY')
        assert '7.94 CNY' in result
        assert 'Assets:Savings:Cash  0.00 CNY' in result

    def test_skips_non_sum_queries(self):
        text = 'date | payee\n2024-01-01 | lunch'
        bql = "SELECT date, payee WHERE account ~ 'Expenses'"
        assert normalize_zero_balance_sums(text, bql, 'CNY') == text

    def test_skips_no_result(self):
        assert normalize_zero_balance_sums('(无结果)', 'SELECT sum(units(position))', 'CNY') == '(无结果)'

    def test_skips_empty_text(self):
        assert normalize_zero_balance_sums('', 'SELECT sum(units(position))', 'CNY') == ''
