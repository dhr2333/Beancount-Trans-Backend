from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings

from project.apps.assistant.services.assistant_service import AssistantService
from project.apps.translate.models import FormatConfig


def _make_tool_call_response(tool_name, arguments, call_id='call_1'):
    tool_call = MagicMock()
    tool_call.id = call_id
    tool_call.function.name = tool_name
    tool_call.function.arguments = arguments

    message = MagicMock()
    message.content = None
    message.tool_calls = [tool_call]

    choice = MagicMock()
    choice.finish_reason = 'tool_calls'
    choice.message = message

    response = MagicMock()
    response.choices = [choice]
    return response


def _make_text_response(text):
    message = MagicMock()
    message.content = text
    message.tool_calls = None

    choice = MagicMock()
    choice.finish_reason = 'stop'
    choice.message = message
    choice.message.model_dump.return_value = {'role': 'assistant', 'content': text}

    response = MagicMock()
    response.choices = [choice]
    return response


@pytest.mark.django_db
class TestAssistantService:
    @override_settings(ASSISTANT_DEEPSEEK_API_KEY='platform-sk-test')
    @patch('project.apps.assistant.services.assistant_service.OpenAI')
    def test_chat_with_tool_calls(self, mock_openai_cls, user, bean_file):
        config = FormatConfig.get_user_config(user)
        config.deepseek_apikey = ''
        config.save()

        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.side_effect = [
            _make_tool_call_response('run_bql', '{"query": "SELECT account LIMIT 1"}'),
            _make_text_response('本月餐饮支出 50 元。'),
        ]

        service = AssistantService(user)
        result = service.chat([{'role': 'user', 'content': '餐饮花了多少？'}])

        assert '50' in result.reply
        assert len(result.queries) == 1
        assert result.api_key_source == 'platform'

    @override_settings(ASSISTANT_DEEPSEEK_API_KEY='')
    def test_chat_without_api_key_raises(self, user, bean_file):
        config = FormatConfig.get_user_config(user)
        config.deepseek_apikey = ''
        config.save()

        service = AssistantService(user)
        with pytest.raises(ValueError, match='未配置 DeepSeek API Key'):
            service.chat([{'role': 'user', 'content': '你好'}])
