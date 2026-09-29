from project.apps.assistant.services.plain_language_mode import (
    PLAIN_LANGUAGE_BLOCK,
    detect_plain_language_mode,
)


class TestPlainLanguageBlock:
    def test_block_contains_key_phrases(self):
        assert '【简明表达模式】' in PLAIN_LANGUAGE_BLOCK
        assert '避免专业术语' in PLAIN_LANGUAGE_BLOCK
        assert '结论先行' in PLAIN_LANGUAGE_BLOCK
        assert '不减少分析深度' in PLAIN_LANGUAGE_BLOCK


class TestDetectPlainLanguageMode:
    def test_self_query_means_normal_mode(self):
        prior = [
            {'bql': 'SELECT 1', 'result_preview': 'x', 'ledger': 'self'},
            {'bql': 'SELECT 2', 'result_preview': 'y', 'ledger': 'wife'},
        ]
        assert detect_plain_language_mode(prior, self_ledger_available=False) is False

    def test_legacy_missing_ledger_treated_as_self(self):
        prior = [{'bql': 'SELECT 1', 'result_preview': 'x'}]
        assert detect_plain_language_mode(prior, self_ledger_available=False) is False
        prior_empty = [{'bql': 'SELECT 1', 'result_preview': 'x', 'ledger': ''}]
        assert detect_plain_language_mode(prior_empty, self_ledger_available=False) is False

    def test_only_shared_query_means_plain_mode(self):
        prior = [{'bql': 'SELECT 1', 'result_preview': 'x', 'ledger': 'wife'}]
        assert detect_plain_language_mode(prior, self_ledger_available=True) is True

    def test_no_history_falls_back_to_self_ledger_availability(self):
        assert detect_plain_language_mode(None, self_ledger_available=False) is True
        assert detect_plain_language_mode([], self_ledger_available=False) is True
        assert detect_plain_language_mode(None, self_ledger_available=True) is False
        assert detect_plain_language_mode([], self_ledger_available=True) is False

    def test_records_without_bql_are_ignored(self):
        prior = [{'result_preview': 'x', 'ledger': 'wife'}]
        assert detect_plain_language_mode(prior, self_ledger_available=True) is False
