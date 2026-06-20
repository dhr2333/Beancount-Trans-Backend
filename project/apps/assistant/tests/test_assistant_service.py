from unittest.mock import MagicMock, patch

import pytest
from datetime import date
from django.test import override_settings

from project.apps.assistant.services.assistant_service import (
    AssistantService,
    REASONER_MODEL,
    StreamEvent,
    build_system_prompt,
    build_tools,
    get_max_bql_runs,
    resolve_assistant_model,
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


def _make_planning_tool_stream(planning: str, tool_name: str, arguments: str, call_id='call_1'):
    chunks = [_make_stream_chunk(content=char) for char in planning]
    chunks.append(_make_tool_call_chunk(0, call_id, tool_name, arguments))
    return iter(chunks)


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


def _make_reasoning_tool_stream(reasoning: str, tool_name: str, arguments: str, call_id='call_1'):
    chunks = [_make_stream_chunk(reasoning_content=char) for char in reasoning]
    chunks.append(_make_tool_call_chunk(0, call_id, tool_name, arguments))
    return iter(chunks)


def _with_guard_retry(*streams):
    """为数字校验重试追加一次安全的 LLM mock 响应。"""
    return [*streams, _make_text_stream('请以查询详情中的 BQL 结果为准。')]


def _collect_events(service, messages, show_bql=False):
    return list(service._iter_chat_events(messages, show_bql=show_bql))


_FOOD_SUM_BQL = (
    '{"query": "SELECT sum(units(position)) WHERE account ~ \'^Expenses:Food\'"}'
)

_DSML_FOOD_BQL = (
    '<｜｜DSML｜｜tool_calls>\n'
    '<｜｜DSML｜｜invoke name="run_bql">\n'
    '<｜｜DSML｜｜parameter name="query" string="true">'
    "SELECT sum(units(position)) WHERE account ~ '^Expenses:Food'"
    '<｜｜DSML｜｜parameter>\n'
    '<｜｜DSML｜｜invoke>\n'
    '<｜｜DSML｜｜tool_calls>'
)

_EMPTY_MONTH_FOOD_BQL = (
    '{"query": "SELECT sum(units(position)) WHERE account ~ \'^Expenses:Food\' '
    "AND year = 2026 AND month = 5\"}"
)


def _make_dsml_content_stream(dsml_text: str):
    return iter([_make_stream_chunk(content=dsml_text)])


@pytest.mark.django_db
class TestAssistantService:
    def test_system_prompt_includes_reference_date_and_bql_examples(self):
        prompt = build_system_prompt(date(2026, 6, 16))
        assert '基准日期（今天）: 2026-06-16' in prompt
        assert '本月' in prompt
        assert '【BQL】' in prompt
        assert 'year = 2026 AND month = 6' in prompt
        assert 'BQL 能力说明' in prompt
        assert '禁止心算' in prompt
        assert 'Markdown' in prompt
        assert '完整标签路径' in prompt
        assert 'IN tags' in prompt
        assert 'tags ~ 或' not in prompt
        assert 'account ~ / tags ~' not in prompt
        assert '描述（账户路径）' in prompt
        assert '余额为 0' in prompt
        assert '账户层级' in prompt
        assert '父账户行仅含直接 posting' in prompt
        assert '复式记账符号' in prompt
        assert 'Income 累计为负表示收入' in prompt

    def test_insight_mode_system_prompt(self):
        prompt = build_system_prompt(date(2026, 6, 16), insight_mode=True)
        assert '【洞察模式】' in prompt
        assert '主动追溯' in prompt
        assert 'tags' in prompt
        assert 'links' in prompt
        assert 'FROM entries' in prompt
        assert 'Balance / Pad' in prompt
        assert '洞察模式 BQL 示例' in prompt

    def test_build_tools_insight_mode_description(self):
        tools = build_tools(insight_mode=True)
        run_bql = next(t for t in tools if t['function']['name'] == 'run_bql')
        desc = run_bql['function']['description']
        assert '洞察模式' in desc
        assert 'FROM entries' in desc
        assert '追溯历史' in desc

    @pytest.mark.django_db
    def test_dispatch_tool_blocks_over_bql_limit(self, user, bean_file):
        service = AssistantService(user)
        queries = []
        bql = "SELECT sum(units(position)) WHERE account ~ 'Assets'"
        for _ in range(service.max_bql_runs):
            service._dispatch_tool('run_bql', {'query': bql}, queries)
        assert len(queries) == service.max_bql_runs
        message = service._dispatch_tool('run_bql', {'query': bql}, queries)
        assert 'BQL 查询上限' in message
        assert len(queries) == service.max_bql_runs

    @override_settings(ASSISTANT_DEEPSEEK_API_KEY='platform-sk-test', ASSISTANT_MAX_BQL_RUNS=5)
    @patch('project.apps.assistant.services.assistant_service.OpenAI')
    def test_chat_stops_after_max_bql_runs(self, mock_openai_cls, user, bean_file):
        config = FormatConfig.get_user_config(user)
        config.deepseek_apikey = ''
        config.save()

        max_runs = get_max_bql_runs()
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.side_effect = [
            *[
                _make_tool_call_stream('run_bql', f'{{"query": "SELECT {i}"}}', f'call_{i}')
                for i in range(1, max_runs + 2)
            ],
            _make_text_stream('根据已有查询，现金与支付宝当前均无余额。'),
        ]

        service = AssistantService(user)
        result = service.chat([{'role': 'user', 'content': '我还有多少现金？'}])

        assert len(result.queries) == max_runs

    @override_settings(ASSISTANT_DEEPSEEK_API_KEY='platform-sk-test')
    @patch('project.apps.assistant.services.assistant_service.OpenAI')
    def test_chat_with_tool_calls(self, mock_openai_cls, user, bean_file):
        config = FormatConfig.get_user_config(user)
        config.deepseek_apikey = ''
        config.save()

        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.side_effect = [
            _make_tool_call_stream('run_bql', _FOOD_SUM_BQL),
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
            _make_text_stream('已完成多轮查询，明细请见查询详情。'),
        ]

        service = AssistantService(user)
        result = service.chat([{'role': 'user', 'content': '本月总支出是多少？'}])

        assert '查询详情' in result.reply
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
            _make_text_stream('根据已有查询整理如下，详见查询详情。'),
        ]

        service = AssistantService(user)
        result = service.chat([{'role': 'user', 'content': '本月支出？'}])

        assert '查询详情' in result.reply
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
            _make_tool_call_stream('run_bql', _FOOD_SUM_BQL),
            _make_text_stream('本月餐饮支出 50 元。'),
        ]

        service = AssistantService(user)
        events = _collect_events(service, [{'role': 'user', 'content': '餐饮花了多少？'}])
        event_types = [e.event for e in events]

        assert event_types[0] == 'status'
        assert 'tool_start' in event_types
        assert 'tool_end' in event_types
        assert 'thinking_delta' not in event_types
        assert 'delta' in event_types
        assert event_types[-1] == 'done'
        assert '50' in events[-1].data['reply']
        assert '执行查询' not in events[-1].data['thinking']
        assert 'Expenses:Food' not in events[-1].data['thinking']
        assert len(events[-1].data['queries']) == 1
        assert 'Expenses:Food' in events[-1].data['queries'][0]['bql']

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

    @override_settings(ASSISTANT_DEEPSEEK_API_KEY='platform-sk-test')
    @patch('project.apps.assistant.services.assistant_service.OpenAI')
    def test_reasoning_delta_emitted_and_in_done(self, mock_openai_cls, user, bean_file):
        config = FormatConfig.get_user_config(user)
        config.deepseek_apikey = ''
        config.save()

        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.side_effect = [
            _make_reasoning_then_text_stream('先分析账户。', '本月支出请结合账户结构查看。'),
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
        assert '支出' in done.data['reply']

    @override_settings(ASSISTANT_DEEPSEEK_API_KEY='platform-sk-test')
    @patch('project.apps.assistant.services.assistant_service.OpenAI')
    def test_planning_text_before_tool_call_in_reasoning(self, mock_openai_cls, user, bean_file):
        config = FormatConfig.get_user_config(user)
        config.deepseek_apikey = ''
        config.save()

        planning = '我先获取账本上下文，了解账户结构。'
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.side_effect = [
            _make_planning_tool_stream(
                planning,
                'get_ledger_context',
                '{}',
            ),
            _make_tool_call_stream('run_bql', _FOOD_SUM_BQL, 'call_2'),
            _make_text_stream('本月餐饮 50 元。'),
        ]

        service = AssistantService(user)
        events = _collect_events(service, [{'role': 'user', 'content': '餐饮多少？'}])
        reasoning_events = [e for e in events if e.event == 'reasoning_delta']
        done = events[-1]

        assert reasoning_events
        assert planning in ''.join(e.data['content'] for e in reasoning_events)
        assert planning in done.data['reasoning']
        assert planning in done.data['thinking']
        assert '50' in done.data['reply']
        assert '50' not in done.data['reasoning']

    @override_settings(ASSISTANT_DEEPSEEK_API_KEY='platform-sk-test')
    @patch('project.apps.assistant.services.assistant_service.OpenAI')
    def test_number_guard_retries_when_reply_has_uncited_amounts(
        self, mock_openai_cls, user, bean_file,
    ):
        config = FormatConfig.get_user_config(user)
        config.deepseek_apikey = ''
        config.save()

        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.side_effect = [
            _make_text_stream('个人应收款合计 **9999** 元。'),
            _make_text_stream('当前未执行账本查询，无法确认具体金额。'),
        ]

        service = AssistantService(user)
        events = _collect_events(service, [{'role': 'user', 'content': '分析个人应收款'}])
        done = events[-1]

        assert done.event == 'done'
        assert mock_client.chat.completions.create.call_count == 2
        assert '9999' not in done.data['reply']

    @override_settings(ASSISTANT_DEEPSEEK_API_KEY='platform-sk-test')
    @patch('project.apps.assistant.services.assistant_service.OpenAI')
    def test_dsml_in_content_executes_bql_without_leaking_markup(
        self, mock_openai_cls, user, bean_file,
    ):
        config = FormatConfig.get_user_config(user)
        config.deepseek_apikey = ''
        config.save()

        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.side_effect = [
            _make_dsml_content_stream(_DSML_FOOD_BQL),
            _make_text_stream('餐饮支出 **50** 元。'),
        ]

        service = AssistantService(user)
        events = _collect_events(service, [{'role': 'user', 'content': '餐饮花了多少？'}])
        done = events[-1]

        assert done.event == 'done'
        assert 'DSML' not in done.data['reply']
        assert len(done.data['queries']) == 1
        assert '50' in done.data['reply']
        assert 'tool_start' in [e.event for e in events]

    @override_settings(ASSISTANT_DEEPSEEK_API_KEY='platform-sk-test')
    @patch('project.apps.assistant.services.assistant_service.OpenAI')
    def test_empty_bql_result_zero_reply_skips_guard_disclaimer(
        self, mock_openai_cls, user, bean_file,
    ):
        config = FormatConfig.get_user_config(user)
        config.deepseek_apikey = ''
        config.save()

        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.side_effect = [
            _make_tool_call_stream('run_bql', _EMPTY_MONTH_FOOD_BQL),
            _make_text_stream('2026年5月餐饮支出为 **0** 元。'),
        ]

        service = AssistantService(user)
        result = service.chat([{'role': 'user', 'content': '上个月餐饮花了多少？'}])

        assert mock_client.chat.completions.create.call_count == 2
        assert '部分金额可能未完全来自' not in result.reply
        assert '0' in result.reply

    def test_resolve_assistant_model(self):
        with override_settings(ASSISTANT_MODEL='deepseek-chat'):
            assert resolve_assistant_model(deep_think=False) == 'deepseek-chat'
            assert resolve_assistant_model(deep_think=True) == REASONER_MODEL

    @override_settings(ASSISTANT_DEEPSEEK_API_KEY='platform-sk-test')
    @patch('project.apps.assistant.services.assistant_service.OpenAI')
    def test_deep_think_selects_reasoner_model(self, mock_openai_cls, user, bean_file):
        config = FormatConfig.get_user_config(user)
        config.deepseek_apikey = ''
        config.save()

        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.side_effect = [
            _make_text_stream('你好。'),
        ]

        service = AssistantService(user, deep_think=True)
        service.chat([{'role': 'user', 'content': '你好'}])

        first_kwargs = mock_client.chat.completions.create.call_args_list[0].kwargs
        assert first_kwargs['model'] == REASONER_MODEL
        assert 'temperature' not in first_kwargs

    @override_settings(ASSISTANT_DEEPSEEK_API_KEY='platform-sk-test')
    @patch('project.apps.assistant.services.assistant_service.OpenAI')
    def test_reasoner_tool_call_roundtrips_reasoning_content(
        self, mock_openai_cls, user, bean_file,
    ):
        config = FormatConfig.get_user_config(user)
        config.deepseek_apikey = ''
        config.save()

        reasoning = '先查餐饮总额。'
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.side_effect = [
            _make_reasoning_tool_stream(reasoning, 'run_bql', _FOOD_SUM_BQL),
            _make_text_stream('餐饮 **50** 元。'),
        ]

        service = AssistantService(user, deep_think=True)
        events = _collect_events(service, [{'role': 'user', 'content': '餐饮多少？'}])
        done = events[-1]

        assert done.event == 'done'
        assert mock_client.chat.completions.create.call_count == 2
        second_messages = mock_client.chat.completions.create.call_args_list[1].kwargs['messages']
        tool_assistant = next(
            m for m in second_messages
            if m.get('role') == 'assistant' and m.get('tool_calls')
        )
        assert tool_assistant['reasoning_content'] == reasoning
        assert '50' in done.data['reply']

    @override_settings(ASSISTANT_DEEPSEEK_API_KEY='platform-sk-test')
    @patch('project.apps.assistant.services.assistant_service.OpenAI')
    def test_chat_model_skips_reasoning_content_in_history(
        self, mock_openai_cls, user, bean_file,
    ):
        config = FormatConfig.get_user_config(user)
        config.deepseek_apikey = ''
        config.save()

        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.side_effect = [
            _make_tool_call_stream('run_bql', _FOOD_SUM_BQL),
            _make_text_stream('餐饮 **50** 元。'),
        ]

        service = AssistantService(user, deep_think=False)
        service.chat([{'role': 'user', 'content': '餐饮多少？'}])

        second_messages = mock_client.chat.completions.create.call_args_list[1].kwargs['messages']
        tool_assistant = next(
            m for m in second_messages
            if m.get('role') == 'assistant' and m.get('tool_calls')
        )
        assert 'reasoning_content' not in tool_assistant
        first_kwargs = mock_client.chat.completions.create.call_args_list[0].kwargs
        assert first_kwargs['model'] == 'deepseek-chat'
        assert first_kwargs.get('temperature') == 0.1
