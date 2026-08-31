import pytest
from django.test import override_settings

from project.apps.assistant.services.api_key_resolver import (
    DEFAULT_ASSISTANT_MODEL,
    OLLAMA_PLACEHOLDER_KEY,
    resolve_api_key,
    resolve_llm_provider,
)
from project.apps.translate.models import FormatConfig


@pytest.mark.django_db
class TestLlmProvider:
    def test_user_key_priority(self, user):
        config = FormatConfig.get_user_config(user)
        config.assistant_api_key = 'user-sk-test'
        config.save()

        provider = resolve_llm_provider(user)
        assert provider.api_key == 'user-sk-test'
        assert provider.source == 'user'
        assert provider.supports_thinking_param is True

        resolved = resolve_api_key(user)
        assert resolved.api_key == 'user-sk-test'
        assert resolved.source == 'user'

    @override_settings(
        ASSISTANT_DEEPSEEK_API_KEY='platform-sk-test',
        ASSISTANT_MODEL=DEFAULT_ASSISTANT_MODEL,
    )
    def test_platform_key_fallback(self, user):
        config = FormatConfig.get_user_config(user)
        config.assistant_api_key = ''
        config.assistant_base_url = ''
        config.save()

        provider = resolve_llm_provider(user)
        assert provider.api_key == 'platform-sk-test'
        assert provider.source == 'platform'
        assert provider.model == DEFAULT_ASSISTANT_MODEL
        assert provider.supports_thinking_param is True

    @override_settings(ASSISTANT_DEEPSEEK_API_KEY='')
    def test_no_key(self, user):
        config = FormatConfig.get_user_config(user)
        config.assistant_api_key = ''
        config.assistant_base_url = ''
        config.save()

        provider = resolve_llm_provider(user)
        assert provider.source == 'none'
        assert provider.configured is False

    def test_user_custom_base_url_without_platform_key(self, user):
        config = FormatConfig.get_user_config(user)
        config.assistant_base_url = 'http://127.0.0.1:11434/v1'
        config.assistant_api_key = ''
        config.assistant_model = 'llama3.1'
        config.save()

        with override_settings(ASSISTANT_DEEPSEEK_API_KEY='platform-sk-test'):
            provider = resolve_llm_provider(user)

        assert provider.source == 'user'
        assert provider.api_key == OLLAMA_PLACEHOLDER_KEY
        assert provider.supports_thinking_param is False
        assert provider.model == 'llama3.1'

    def test_migration_copy_from_deepseek_apikey(self, user):
        config = FormatConfig.get_user_config(user)
        config.deepseek_apikey = 'legacy-sk-test'
        config.assistant_api_key = 'legacy-sk-test'
        config.save()

        provider = resolve_llm_provider(user)
        assert provider.source == 'user'
        assert provider.api_key == 'legacy-sk-test'
