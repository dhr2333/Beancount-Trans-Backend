from project.apps.assistant.services.result_enricher import enrich_bql_result_text


class TestResultEnricher:
    def test_replaces_account_path_with_description(self):
        text = """   account     sum(position)
-------------  -----------
Expenses:Food  -100.00 CNY
"""
        path_map = {'Expenses:Food': '餐饮'}
        enriched = enrich_bql_result_text(text, path_map)
        assert '餐饮（Expenses:Food）' in enriched
        assert enriched.count('Expenses:Food') == 1

    def test_longer_path_replaced_before_shorter(self):
        text = 'Expenses:Food:Lunch 50.00\nExpenses:Food 100.00'
        path_map = {
            'Expenses:Food': '餐饮',
            'Expenses:Food:Lunch': '午餐',
        }
        enriched = enrich_bql_result_text(text, path_map)
        assert '午餐（Expenses:Food:Lunch）' in enriched
        assert '餐饮（Expenses:Food）' in enriched

    def test_empty_map_returns_unchanged(self):
        text = 'Expenses:Food'
        assert enrich_bql_result_text(text, {}) == text

    def test_empty_description_skipped(self):
        text = 'Expenses:Food'
        assert enrich_bql_result_text(text, {'Expenses:Food': ''}) == text
