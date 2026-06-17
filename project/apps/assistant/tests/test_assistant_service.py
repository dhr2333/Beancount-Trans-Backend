from unittest.mock import MagicMock, patch

import pytest
from datetime import date
from django.test import override_settings

from project.apps.assistant.services.assistant_service import AssistantService, build_system_prompt
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
    def test_system_prompt_includes_reference_date(self):
        prompt = build_system_prompt(date(2026, 6, 16))
        assert '基准日期（今天）: 2026-06-16' in prompt
        assert '本月' in prompt

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

    @override_settings(ASSISTANT_DEEPSEEK_API_KEY='platform-sk-test')
    @patch('project.apps.assistant.services.assistant_service.OpenAI')
    def test_chat_with_multiple_tool_rounds_before_reply(self, mock_openai_cls, user, bean_file):
        """复现日志场景：get_ledger_context + 3x run_bql 后应仍能返回最终回复。"""
        config = FormatConfig.get_user_config(user)
        config.deepseek_apikey = ''
        config.save()

        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.side_effect = [
            _make_tool_call_response('get_ledger_context', '{}'),
            _make_tool_call_response('run_bql', '{"query": "SELECT 1"}', 'call_2'),
            _make_tool_call_response('run_bql', '{"query": "SELECT 2"}', 'call_3'),
            _make_tool_call_response('run_bql', '{"query": "SELECT 3"}', 'call_4'),
            _make_text_response('本月总支出 1000 元。'),
        ]

        service = AssistantService(user)
        result = service.chat([{'role': 'user', 'content': '本月总支出是多少？'}])

        assert '1000' in result.reply
        assert len(result.queries) == 3
        assert '查询步骤过多' not in result.reply

    @override_settings(ASSISTANT_DEEPSEEK_API_KEY='platform-sk-test')
    @patch('project.apps.assistant.services.assistant_service.OpenAI')
    def test_chat_forces_synthesis_when_tool_limit_exceeded(self, mock_openai_cls, user, bean_file):
        """超过工具轮次上限时，应强制汇总而非返回错误提示。"""
        config = FormatConfig.get_user_config(user)
        config.deepseek_apikey = ''
        config.save()

        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        tool_responses = [
            _make_tool_call_response('run_bql', '{"query": "SELECT 1"}', f'call_{i}')
            for i in range(AssistantService.MAX_TOOL_ROUNDS + 1)
        ]
        mock_client.chat.completions.create.side_effect = [
            *tool_responses,
            _make_text_response('根据已有查询，本月支出约 800 元。'),
        ]

        service = AssistantService(user)
        result = service.chat([{'role': 'user', 'content': '本月支出？'}])

        assert '800' in result.reply
        assert '查询步骤过多' not in result.reply
        assert mock_client.chat.completions.create.call_count == AssistantService.MAX_TOOL_ROUNDS + 2

    @override_settings(ASSISTANT_DEEPSEEK_API_KEY='')
    def test_chat_without_api_key_raises(self, user, bean_file):
        config = FormatConfig.get_user_config(user)
        config.deepseek_apikey = ''
        config.save()

        service = AssistantService(user)
        with pytest.raises(ValueError, match='未配置 DeepSeek API Key'):
            service.chat([{'role': 'user', 'content': '你好'}])
