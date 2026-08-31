from unittest.mock import patch

from django.test import override_settings

from project.apps.assistant.services.key_tester import (
    EMPTY_LOCAL,
    EMPTY_WITH_PLATFORM,
    EMPTY_WITHOUT_PLATFORM,
    SUCCESS,
    evaluate_assistant_key,
)


class TestEvaluateAssistantKey:
    @override_settings(ASSISTANT_DEEPSEEK_API_KEY='platform-sk')
    def test_empty_key_allows_copilot_not_parse(self):
        result = evaluate_assistant_key(api_key='', base_url='', model='')
        assert result.ok is True
        assert result.copilot_available is True
        assert result.parse_available is False
        assert result.detail == EMPTY_WITH_PLATFORM

    @override_settings(ASSISTANT_DEEPSEEK_API_KEY='')
    def test_empty_key_without_platform_blocks_both(self):
        result = evaluate_assistant_key(
            api_key='',
            base_url='https://api.deepseek.com',
            model='',
        )
        assert result.ok is False
        assert result.copilot_available is False
        assert result.parse_available is False
        assert result.detail == EMPTY_WITHOUT_PLATFORM

    def test_empty_key_on_local_provider_allows_copilot_not_parse(self):
        result = evaluate_assistant_key(
            api_key='',
            base_url='http://127.0.0.1:11434/v1',
            model='llama3.1',
        )
        assert result.ok is True
        assert result.copilot_available is True
        assert result.parse_available is False
        assert result.detail == EMPTY_LOCAL

    @patch('project.apps.assistant.services.key_tester.probe_llm_connection')
    def test_filled_key_enables_copilot_and_parse(self, mock_probe):
        result = evaluate_assistant_key(
            api_key='user-sk-test',
            base_url='https://api.deepseek.com',
            model='deepseek-v4-flash',
        )
        mock_probe.assert_called_once()
        assert result.ok is True
        assert result.copilot_available is True
        assert result.parse_available is True
        assert result.detail == SUCCESS

    @patch(
        'project.apps.assistant.services.key_tester.probe_llm_connection',
        side_effect=ValueError('密钥无效'),
    )
    def test_invalid_filled_key_blocks_both(self, mock_probe):
        result = evaluate_assistant_key(
            api_key='bad-key',
            base_url='https://api.deepseek.com',
            model='deepseek-v4-flash',
        )
        mock_probe.assert_called_once()
        assert result.ok is False
        assert result.copilot_available is False
        assert result.parse_available is False
        assert '密钥测试失败' in result.detail
