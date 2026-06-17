from unittest.mock import MagicMock, patch

import pytest
from datetime import date
from django.test import override_settings

from project.apps.assistant.services.assistant_service import (
    AssistantService,
    StreamEvent,
    build_system_prompt,
    merge_thinking_text,
)
from project.apps.translate.models import FormatConfig


def _make_stream_chunk(*, content=None, reasoning_content=None, tool_call=None, finish_reason=None):
    chunk = MagicMock()
    choice = MagicMock()
    delta = MagicMock()
    delta.content = content
    delta.reasoning_content = reasoning_content
    delta.tool_calls = [tool_call] if tool_call else None
    choice.delta = delta
    choice.finish_reason = finish_reason
    chunk.choices = [choice]
    return chunk


def _make_tool_call_chunk(index, call_id, name, arguments_fragment):
    tool_call = MagicMock()
    tool_call.index = index
    tool_call.id = call_id
    tool_call.function = MagicMock()
    tool_call.function.name = name
    tool_call.function.arguments = arguments_fragment
    return _make_stream_chunk(tool_call=tool_call)


def _make_tool_call_stream(tool_name, arguments, call_id='call_1'):
    return iter([
        _make_tool_call_chunk(0, call_id, tool_name, arguments),
    ])


def _make_text_stream(text):
    chunks = [_make_stream_chunk(content=char) for char in text]
    chunks.append(_make_stream_chunk(finish_reason='stop'))
    return iter(chunks)


def _make_reasoning_then_text_stream(reasoning: str, answer: str):
    chunks = [_make_stream_chunk(reasoning_content=char) for char in reasoning]
    chunks.extend(_make_stream_chunk(content=char) for char in answer)
    chunks.append(_make_stream_chunk(finish_reason='stop'))
    return iter(chunks)


def _collect_events(service, messages, show_bql=False):
    return list(service._iter_chat_events(messages, show_bql=show_bql))


@pytest.mark.django_db
class TestAssistantService:
    def test_system_prompt_includes_reference_date_and_bql_examples(self):
        prompt = build_system_prompt(date(2026, 6, 16))
        assert '基准日期（今天）: 2026-06-16' in prompt
        assert '本月' in prompt
        assert '【BQL】' in prompt
        assert 'year = 2026 AND month = 6' in prompt
        assert 'BQL 能力说明' in prompt
        assert 'Markdown' in prompt
        assert '平台账户目录' in prompt
        assert '描述（账户路径）' in prompt

    @override_settings(ASSISTANT_DEEPSEEK_API_KEY='platform-sk-test')
    @patch('project.apps.assistant.services.assistant_service.OpenAI')
    def test_chat_with_tool_calls(self, mock_openai_cls, user, bean_file):
        config = FormatConfig.get_user_config(user)
        config.deepseek_apikey = ''
        config.save()

        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.side_effect = [
            _make_tool_call_stream('run_bql', '{"query": "SELECT account LIMIT 1"}'),
            _make_text_stream('本月餐饮支出 50 元。'),
        ]

        service = AssistantService(user)
        result = service.chat([{'role': 'user', 'content': '餐饮花了多少？'}])

        assert '50' in result.reply
        assert len(result.queries) == 1
        assert result.api_key_source == 'platform'

    @override_settings(ASSISTANT_DEEPSEEK_API_KEY='platform-sk-test')
    @patch('project.apps.assistant.services.assistant_service.OpenAI')
    def test_chat_with_multiple_tool_rounds_before_reply(self, mock_openai_cls, user, bean_file):
        config = FormatConfig.get_user_config(user)
        config.deepseek_apikey = ''
        config.save()

        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.side_effect = [
            _make_tool_call_stream('get_ledger_context', '{}'),
            _make_tool_call_stream('run_bql', '{"query": "SELECT 1"}', 'call_2'),
            _make_tool_call_stream('run_bql', '{"query": "SELECT 2"}', 'call_3'),
            _make_tool_call_stream('run_bql', '{"query": "SELECT 3"}', 'call_4'),
            _make_text_stream('本月总支出 1000 元。'),
        ]

        service = AssistantService(user)
        result = service.chat([{'role': 'user', 'content': '本月总支出是多少？'}])

        assert '1000' in result.reply
        assert len(result.queries) == 3
        assert '查询步骤过多' not in result.reply

    @override_settings(ASSISTANT_DEEPSEEK_API_KEY='platform-sk-test')
    @patch('project.apps.assistant.services.assistant_service.OpenAI')
    def test_chat_forces_synthesis_when_tool_limit_exceeded(self, mock_openai_cls, user, bean_file):
        config = FormatConfig.get_user_config(user)
        config.deepseek_apikey = ''
        config.save()

        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        tool_streams = [
            _make_tool_call_stream('run_bql', '{"query": "SELECT 1"}', f'call_{i}')
            for i in range(AssistantService.MAX_TOOL_ROUNDS + 1)
        ]
        mock_client.chat.completions.create.side_effect = [
            *tool_streams,
            _make_text_stream('根据已有查询，本月支出约 800 元。'),
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

    @override_settings(ASSISTANT_DEEPSEEK_API_KEY='platform-sk-test')
    @patch('project.apps.assistant.services.assistant_service.OpenAI')
    def test_iter_chat_events_emits_sse_sequence(self, mock_openai_cls, user, bean_file):
        config = FormatConfig.get_user_config(user)
        config.deepseek_apikey = ''
        config.save()

        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.side_effect = [
            _make_tool_call_stream('run_bql', '{"query": "SELECT account LIMIT 1"}'),
            _make_text_stream('本月餐饮支出 50 元。'),
        ]

        service = AssistantService(user)
        events = _collect_events(service, [{'role': 'user', 'content': '餐饮花了多少？'}])
        event_types = [e.event for e in events]

        assert event_types[0] == 'status'
        assert 'tool_start' in event_types
        assert 'tool_end' in event_types
        assert 'thinking_delta' in event_types
        assert 'delta' in event_types
        assert event_types[-1] == 'done'
        assert '50' in events[-1].data['reply']
        assert '执行查询' in events[-1].data['thinking']
        assert 'SELECT account LIMIT 1' in events[-1].data['thinking']

    @override_settings(ASSISTANT_DEEPSEEK_API_KEY='platform-sk-test')
    @patch('project.apps.assistant.services.assistant_service.OpenAI')
    def test_chat_stream_yields_formatted_sse(self, mock_openai_cls, user, bean_file):
        config = FormatConfig.get_user_config(user)
        config.deepseek_apikey = ''
        config.save()

        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.side_effect = [
            _make_text_stream('你好。'),
        ]

        service = AssistantService(user)
        chunks = list(service.chat_stream([{'role': 'user', 'content': '你好'}]))

        assert any('event: done' in chunk for chunk in chunks)
        assert any('event: delta' in chunk for chunk in chunks)

    @override_settings(ASSISTANT_DEEPSEEK_API_KEY='platform-sk-test')
    @patch('project.apps.assistant.services.assistant_service.OpenAI')
    def test_text_reply_streams_deltas_during_llm_round(self, mock_openai_cls, user, bean_file):
        config = FormatConfig.get_user_config(user)
        config.deepseek_apikey = ''
        config.save()

        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.side_effect = [
            _make_text_stream('你好。'),
        ]

        service = AssistantService(user)
        events = _collect_events(service, [{'role': 'user', 'content': '你好'}])
        event_types = [e.event for e in events]

        writing_idx = event_types.index('status', 1)
        first_delta_idx = event_types.index('delta')
        assert events[writing_idx].data['phase'] == 'writing'
        assert writing_idx < first_delta_idx
        assert event_types[-1] == 'done'

    def test_merge_thinking_text(self):
        assert merge_thinking_text('推理', '步骤') == '推理\n\n---\n\n步骤'
        assert merge_thinking_text('', '步骤') == '步骤'
        assert merge_thinking_text('推理', '') == '推理'

    @override_settings(ASSISTANT_DEEPSEEK_API_KEY='platform-sk-test')
    @patch('project.apps.assistant.services.assistant_service.OpenAI')
    def test_reasoning_delta_emitted_and_in_done(self, mock_openai_cls, user, bean_file):
        config = FormatConfig.get_user_config(user)
        config.deepseek_apikey = ''
        config.save()

        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.side_effect = [
            _make_reasoning_then_text_stream('先分析账户。', '本月 100 元。'),
        ]

        service = AssistantService(user)
        events = _collect_events(service, [{'role': 'user', 'content': '本月支出？'}])
        event_types = [e.event for e in events]

        assert 'reasoning_delta' in event_types
        reasoning_idx = event_types.index('reasoning_delta')
        delta_idx = event_types.index('delta')
        assert reasoning_idx < delta_idx
        done = events[-1]
        assert done.event == 'done'
        assert '先分析账户' in done.data['reasoning']
        assert '先分析账户' in done.data['thinking']
        assert '100' in done.data['reply']
