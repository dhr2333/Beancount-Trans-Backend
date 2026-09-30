from project.apps.assistant.services.plain_language_mode import (
    PLAIN_LANGUAGE_BLOCK,
    SHARED_PLAIN_CONDITION_HEADER,
    build_plain_language_prompt_block,
    detect_plain_language_mode,
)


class TestPlainLanguageBlock:
    def test_block_contains_key_phrases(self):
        assert '【简明表达模式】' in PLAIN_LANGUAGE_BLOCK
        assert 'BQL' in PLAIN_LANGUAGE_BLOCK
        assert '平铺' in PLAIN_LANGUAGE_BLOCK
        assert '父子层级' in PLAIN_LANGUAGE_BLOCK
        assert '没有查到' in PLAIN_LANGUAGE_BLOCK

    def test_prompt_block_forced_vs_conditional(self):
        assert build_plain_language_prompt_block(forced=True) == PLAIN_LANGUAGE_BLOCK

        conditional = build_plain_language_prompt_block(forced=False)
        assert SHARED_PLAIN_CONDITION_HEADER in conditional
        assert PLAIN_LANGUAGE_BLOCK in conditional


class TestDetectPlainLanguageMode:
    def test_missing_self_ledger_is_always_plain(self):
        assert detect_plain_language_mode(self_ledger_available=False) is True
        assert detect_plain_language_mode(
            self_ledger_available=False,
            last_user_message='我的开销怎样',
            shared_ledger_keys=['dhr2333'],
        ) is True

    def test_naming_shared_ledger_forces_plain(self):
        assert detect_plain_language_mode(
            self_ledger_available=True,
            last_user_message='dhr2333 上个月的开销怎样？',
            shared_ledger_keys=['dhr2333'],
        ) is True

    def test_naming_shared_and_self_ledger_is_not_forced(self):
        assert detect_plain_language_mode(
            self_ledger_available=True,
            last_user_message='dhr2333 和我谁花得多',
            shared_ledger_keys=['dhr2333'],
        ) is False

    def test_without_shared_mention_keeps_default(self):
        assert detect_plain_language_mode(
            self_ledger_available=True,
            last_user_message='上个月的开销怎样',
            shared_ledger_keys=['dhr2333'],
        ) is False

    def test_no_shared_ledgers_keeps_default(self):
        assert detect_plain_language_mode(
            self_ledger_available=True,
            last_user_message='上个月的开销怎样',
            shared_ledger_keys=[],
        ) is False
