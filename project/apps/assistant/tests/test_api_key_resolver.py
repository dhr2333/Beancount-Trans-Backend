import pytest
from django.test import override_settings

from project.apps.assistant.services.api_key_resolver import resolve_api_key
from project.apps.translate.models import FormatConfig


@pytest.mark.django_db
class TestApiKeyResolver:
    def test_user_key_priority(self, user):
        config = FormatConfig.get_user_config(user)
        config.deepseek_apikey = 'user-sk-test'
        config.save()

        resolved = resolve_api_key(user)
        assert resolved.api_key == 'user-sk-test'
        assert resolved.source == 'user'

    @override_settings(ASSISTANT_DEEPSEEK_API_KEY='platform-sk-test')
    def test_platform_key_fallback(self, user):
        config = FormatConfig.get_user_config(user)
        config.deepseek_apikey = ''
        config.save()

        resolved = resolve_api_key(user)
        assert resolved.api_key == 'platform-sk-test'
        assert resolved.source == 'platform'

    @override_settings(ASSISTANT_DEEPSEEK_API_KEY='')
    def test_no_key(self, user):
        config = FormatConfig.get_user_config(user)
        config.deepseek_apikey = ''
        config.save()

        resolved = resolve_api_key(user)
        assert resolved.api_key is None
        assert resolved.source == 'none'
