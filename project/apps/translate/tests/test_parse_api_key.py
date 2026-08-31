from types import SimpleNamespace

import pytest

from project.apps.translate.models import FormatConfig
from project.apps.translate.serializers import FormatConfigSerializer
from project.apps.translate.services.parse_api_key import resolve_parse_deepseek_api_key


class TestResolveParseDeepseekApiKey:
    def test_empty_assistant_key_does_not_use_legacy_or_platform_fields(self):
        config = SimpleNamespace(
            assistant_api_key='',
            deepseek_apikey='legacy-sk',
        )
        assert resolve_parse_deepseek_api_key(config) == ''

    def test_filled_assistant_key_is_used_for_parse(self):
        config = SimpleNamespace(
            assistant_api_key=' user-sk-test ',
            deepseek_apikey='legacy-sk',
        )
        assert resolve_parse_deepseek_api_key(config) == 'user-sk-test'


@pytest.mark.django_db
class TestFormatConfigDeepSeekKey:
    def test_deepseek_without_copilot_key_is_rejected(self, user):
        config = FormatConfig.get_user_config(user)
        serializer = FormatConfigSerializer(
            config,
            data={'ai_model': 'DeepSeek', 'assistant_api_key': ''},
            partial=True,
        )
        assert serializer.is_valid() is False
        assert 'ai_model' in serializer.errors

    def test_deepseek_with_copilot_key_syncs_legacy_field(self, user):
        config = FormatConfig.get_user_config(user)
        serializer = FormatConfigSerializer(
            config,
            data={'ai_model': 'DeepSeek', 'assistant_api_key': 'user-sk-test'},
            partial=True,
        )
        assert serializer.is_valid(), serializer.errors
        serializer.save()
        config.refresh_from_db()
        assert config.assistant_api_key == 'user-sk-test'
        assert config.deepseek_apikey == 'user-sk-test'
