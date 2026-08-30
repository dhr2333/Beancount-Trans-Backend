from project.apps.assistant.services.api_key_resolver import LlmProvider
from project.apps.assistant.services.thinking_params import (
    build_completion_extras,
    is_thinking_enabled,
)


class TestThinkingParams:
    def test_deep_think_enabled_for_deepseek(self):
        provider = LlmProvider(
            base_url='https://api.deepseek.com',
            api_key='sk-test',
            model='deepseek-v4-flash',
            supports_thinking_param=True,
            source='user',
        )
        assert is_thinking_enabled(provider, deep_think=True) is True
        extras = build_completion_extras(provider, deep_think=True)
        assert extras == {'extra_body': {'thinking': {'type': 'enabled'}}}

    def test_deep_think_disabled_without_flag(self):
        provider = LlmProvider(
            base_url='https://api.deepseek.com',
            api_key='sk-test',
            model='deepseek-v4-flash',
            supports_thinking_param=True,
            source='user',
        )
        assert is_thinking_enabled(provider, deep_think=False) is False
        assert build_completion_extras(provider, deep_think=False) == {}

    def test_deep_think_ignored_for_ollama(self):
        provider = LlmProvider(
            base_url='http://127.0.0.1:11434/v1',
            api_key='ollama',
            model='llama3.1',
            supports_thinking_param=False,
            source='user',
        )
        assert is_thinking_enabled(provider, deep_think=True) is False
        assert build_completion_extras(provider, deep_think=True) == {}
