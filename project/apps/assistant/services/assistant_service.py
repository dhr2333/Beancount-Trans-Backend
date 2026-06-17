"""LLM 编排：DeepSeek function calling + BQL 工具。"""
import json
import logging
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from django.conf import settings
from django.contrib.auth.models import User
from openai import OpenAI

from .api_key_resolver import resolve_api_key
from .bql_reference import build_bql_capability_reference
from .bql_validator import BQLValidationError
from .ledger_query import LedgerNotFoundError, LedgerQueryService
from .reference_date import build_reference_date_context, get_reference_date
from .schema_provider import build_bql_examples, get_ledger_context

logger = logging.getLogger(__name__)

THINKING_PREVIEW_MAX_LEN = 800


def merge_thinking_text(reasoning: str, agent: str) -> str:
    reasoning = reasoning.strip()
    agent = agent.strip()
    if reasoning and agent:
        return f'{reasoning}\n\n---\n\n{agent}'
    return reasoning or agent


def truncate_thinking_preview(text: str) -> str:
    if len(text) <= THINKING_PREVIEW_MAX_LEN:
        return text
    return f'{text[:THINKING_PREVIEW_MAX_LEN]}\n…（已截断，完整结果见「查询详情」）'


def format_tool_thinking_start(fn_name: str, fn_args: dict[str, Any]) -> str:
    if fn_name == 'get_ledger_context':
        return '\n\n### 获取账本上下文\n'
    if fn_name == 'run_bql':
        query = fn_args.get('query', '')
        return f'\n\n### 执行查询\n```bql\n{query}\n```\n'
    return f'\n\n### 调用 {fn_name}\n'


def format_tool_thinking_end(fn_name: str, tool_result: str) -> str:
    if fn_name == 'get_ledger_context':
        return ''
    preview = truncate_thinking_preview(tool_result)
    return f'\n**结果预览**\n```\n{preview}\n```\n'

SYSTEM_PROMPT_TEMPLATE = """你是 Beancount-Trans 的个人账本助手。你只能基于工具返回的真实数据回答用户问题。

{reference_date_context}

规则：
1. 回答支出、收入、余额、汇总类问题时，必须先调用 run_bql 执行查询，不要编造数字。
2. 不确定账户名称时，先调用 get_ledger_context 了解平台账户/标签目录、账本账户列表和 BQL 语法。
3. 用户提及支出/收入类别（如「餐饮」「交通」）时，先对照 get_ledger_context 中的「平台账户目录」描述匹配，再写 account ~ 正则（子科目用 ^Expenses:Food 等形式）。
4. 涉及消费性质（必要/非必要、线上/线下等）时，对照「平台标签目录」，BQL 用 tags ~ 或具体标签名筛选。
5. 展示结果时：有平台描述则写「描述（账户路径）」；无描述则用账户路径；表格汇总同样遵循。
6. 生成 BQL 时严格遵守「BQL 能力说明」与下方示例；账户用 account ~ 正则；金额过滤用 number 列，禁止 units(position) > N。
7. 涉及「本月」「上月」「最近」等时间时，以上述基准日期为准构造 BQL 日期条件。
8. 用中文简洁回答，优先使用 Markdown 结构化展示，标明货币单位；若查无数据，明确说明。
9. 同一问题最多调用 run_bql 3 次；若仍无满意结果，请根据已有查询结果作答，不要无限重试。
10. 不要执行写操作，不要讨论与账本无关的话题。
11. 使用 Markdown 格式化回答：金额与关键数字用 **粗体**；多项对比用 Markdown 表格；列举用有序/无序列表；不要输出原始 HTML。

{bql_capability_reference}

{bql_examples}"""


def build_system_prompt(reference_date: date | None = None) -> str:
    ref = reference_date or get_reference_date()
    return SYSTEM_PROMPT_TEMPLATE.format(
        reference_date_context=build_reference_date_context(ref),
        bql_capability_reference=build_bql_capability_reference(),
        bql_examples=build_bql_examples(ref),
    )


def format_sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


TOOLS = [
    {
        'type': 'function',
        'function': {
            'name': 'get_ledger_context',
            'description': (
                '获取用户账本上下文：平台账户/标签目录（含描述）、'
                '账本实际账户、默认货币、BQL 语法说明与查询示例'
            ),
            'parameters': {'type': 'object', 'properties': {}, 'required': []},
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'run_bql',
            'description': (
                '执行只读 BQL 查询并返回表格结果。必须 SELECT 开头；'
                '用户说的类别名称先对照平台账户/标签目录映射到 account ~ / tags ~；'
                '账户用 account ~ 正则；时间用 year/month 或 date 范围；'
                '金额过滤用 number > N，禁止 units(position) > N；'
                '遵守 system prompt 中的 BQL 能力说明与示例。'
            ),
            'parameters': {
                'type': 'object',
                'properties': {
                    'query': {
                        'type': 'string',
                        'description': 'BQL SELECT 查询语句，参考示例写法',
                    }
                },
                'required': ['query'],
            },
        },
    },
]


@dataclass
class QueryRecord:
    bql: str
    result_preview: str


@dataclass
class AssistantReply:
    reply: str
    queries: list[QueryRecord] = field(default_factory=list)
    api_key_source: str = 'none'
    thinking: str = ''
    reasoning: str = ''


@dataclass
class StreamEvent:
    event: str
    data: dict[str, Any]


@dataclass
class _AccumulatedToolCall:
    id: str = ''
    name: str = ''
    arguments: str = ''


@dataclass
class _StreamRoundResult:
    content_parts: list[str]
    tool_calls: list[_AccumulatedToolCall]
    reasoning_parts: list[str] = field(default_factory=list)


class AssistantService:
    MAX_TOOL_ROUNDS = 8
    MAX_MESSAGES = 20

    def __init__(self, user: User, reference_date: date | None = None):
        self.user = user
        self.reference_date = reference_date or get_reference_date()
        self.ledger_query = LedgerQueryService(user)
        self.model = getattr(settings, 'ASSISTANT_MODEL', 'deepseek-chat')

    def _build_client(self, api_key: str) -> OpenAI:
        return OpenAI(api_key=api_key, base_url='https://api.deepseek.com')

    def _dispatch_tool(self, name: str, arguments: dict[str, Any], queries: list[QueryRecord]) -> str:
        if name == 'get_ledger_context':
            return get_ledger_context(self.user, reference_date=self.reference_date)

        if name == 'run_bql':
            query = arguments.get('query', '')
            try:
                result = self.ledger_query.execute(query)
                queries.append(QueryRecord(bql=result.bql, result_preview=result.result_text))
                return result.result_text
            except BQLValidationError as exc:
                return str(exc)
            except ValueError as exc:
                return str(exc)
            except Exception as exc:
                return f'查询失败: {exc}'

        return f'未知工具: {name}'

    def _finalize_reply(
        self,
        reply_text: str,
        queries: list[QueryRecord],
        show_bql: bool,
        api_key_source: str,
        *,
        reasoning: str = '',
        thinking: str = '',
    ) -> AssistantReply:
        if not reply_text:
            reply_text = '抱歉，我暂时无法回答这个问题，请尝试换个问法。'

        if show_bql and queries:
            bql_section = '\n\n'.join(
                f'```bql\n{q.bql}\n```\n{q.result_preview}' for q in queries
            )
            reply_text = f'{reply_text}\n\n---\n查询详情:\n{bql_section}'

        return AssistantReply(
            reply=reply_text,
            queries=queries,
            api_key_source=api_key_source,
            thinking=thinking,
            reasoning=reasoning,
        )

    def _done_event_data(self, reply: AssistantReply) -> dict[str, Any]:
        return {
            'reply': reply.reply,
            'queries': [
                {'bql': q.bql, 'result_preview': q.result_preview}
                for q in reply.queries
            ],
            'api_key_source': reply.api_key_source,
            'thinking': reply.thinking,
            'reasoning': reply.reasoning,
        }

    def _build_thinking_reply(
        self,
        reply_text: str,
        queries: list[QueryRecord],
        show_bql: bool,
        api_key_source: str,
        reasoning_parts: list[str],
        thinking_parts: list[str],
    ) -> AssistantReply:
        reasoning_text = ''.join(reasoning_parts)
        agent_text = ''.join(thinking_parts)
        merged = merge_thinking_text(reasoning_text, agent_text)
        return self._finalize_reply(
            reply_text,
            queries,
            show_bql,
            api_key_source,
            reasoning=reasoning_text,
            thinking=merged,
        )

    def _run_llm_round(
        self,
        client: OpenAI,
        llm_messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | None = None,
        stream_text: bool = False,
    ) -> Iterator[StreamEvent | _StreamRoundResult]:
        kwargs: dict[str, Any] = {
            'model': self.model,
            'messages': llm_messages,
            'temperature': 0.1,
            'stream': True,
        }
        if tools is not None:
            kwargs['tools'] = tools
        if tool_choice is not None:
            kwargs['tool_choice'] = tool_choice

        content_parts: list[str] = []
        reasoning_parts: list[str] = []
        tool_calls_map: dict[int, _AccumulatedToolCall] = {}

        stream = client.chat.completions.create(**kwargs)
        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.tool_calls:
                for tool_call in delta.tool_calls:
                    entry = tool_calls_map.setdefault(tool_call.index, _AccumulatedToolCall())
                    if tool_call.id:
                        entry.id = tool_call.id
                    if tool_call.function.name:
                        entry.name = tool_call.function.name
                    if tool_call.function.arguments:
                        entry.arguments += tool_call.function.arguments
            reasoning_content = getattr(delta, 'reasoning_content', None)
            if reasoning_content:
                reasoning_parts.append(reasoning_content)
                if stream_text:
                    yield StreamEvent('reasoning_delta', {'content': reasoning_content})
            if delta.content:
                content_parts.append(delta.content)
                if stream_text and not tool_calls_map:
                    yield StreamEvent('delta', {'content': delta.content})

        yield _StreamRoundResult(
            content_parts=content_parts,
            tool_calls=[tool_calls_map[i] for i in sorted(tool_calls_map)],
            reasoning_parts=reasoning_parts,
        )

    def _assistant_message_from_tool_calls(
        self,
        tool_calls: list[_AccumulatedToolCall],
    ) -> dict[str, Any]:
        return {
            'role': 'assistant',
            'content': None,
            'tool_calls': [
                {
                    'id': tc.id,
                    'type': 'function',
                    'function': {'name': tc.name, 'arguments': tc.arguments},
                }
                for tc in tool_calls
            ],
        }

    def _iter_force_final_reply(
        self,
        client: OpenAI,
        llm_messages: list[dict[str, Any]],
        queries: list[QueryRecord],
        show_bql: bool,
        api_key_source: str,
        reasoning_parts: list[str],
        thinking_parts: list[str],
    ) -> Iterator[StreamEvent]:
        synthesis_messages = [
            *llm_messages,
            {
                'role': 'user',
                'content': (
                    '已达到工具调用次数上限。请仅根据上文工具已返回的查询结果，'
                    '用中文直接回答用户最初的问题；若数据不足请说明，不要编造数字。'
                ),
            },
        ]
        yield StreamEvent('status', {'phase': 'writing'})
        content_parts: list[str] = []
        for item in self._run_llm_round(client, synthesis_messages, stream_text=True):
            if isinstance(item, StreamEvent):
                if item.event == 'reasoning_delta':
                    reasoning_parts.append(item.data['content'])
                yield item
            else:
                content_parts = item.content_parts

        reply_text = ''.join(content_parts).strip()
        final = self._build_thinking_reply(
            reply_text, queries, show_bql, api_key_source, reasoning_parts, thinking_parts,
        )
        yield StreamEvent('done', self._done_event_data(final))

    def _iter_chat_events(
        self,
        messages: list[dict[str, str]],
        show_bql: bool = False,
    ) -> Iterator[StreamEvent]:
        resolved = resolve_api_key(self.user)
        if not resolved.api_key:
            raise ValueError(
                '未配置 DeepSeek API Key，请在「输出配置」中填写，或联系管理员配置平台 Key。'
            )

        if not self.ledger_query.ledger_exists():
            raise LedgerNotFoundError('账本文件尚未创建，请先上传并解析账单。')

        if len(messages) > self.MAX_MESSAGES:
            messages = messages[-self.MAX_MESSAGES:]

        client = self._build_client(resolved.api_key)
        queries: list[QueryRecord] = []
        llm_messages: list[dict[str, Any]] = [
            {'role': 'system', 'content': build_system_prompt(self.reference_date)},
            *messages,
        ]

        yield StreamEvent('status', {'phase': 'thinking'})
        tool_round = 0
        reasoning_parts: list[str] = []
        thinking_parts: list[str] = []

        while True:
            round_result: _StreamRoundResult | None = None
            writing_status_sent = False
            for item in self._run_llm_round(
                client,
                llm_messages,
                tools=TOOLS,
                tool_choice='auto',
                stream_text=True,
            ):
                if isinstance(item, StreamEvent):
                    if item.event == 'reasoning_delta':
                        reasoning_parts.append(item.data['content'])
                    if item.event == 'delta' and not writing_status_sent:
                        yield StreamEvent('status', {'phase': 'writing'})
                        writing_status_sent = True
                    yield item
                else:
                    round_result = item

            if round_result is None:
                raise RuntimeError('LLM 轮次未返回结果')

            if round_result.tool_calls:
                tool_round += 1
                if tool_round > self.MAX_TOOL_ROUNDS:
                    yield from self._iter_force_final_reply(
                        client,
                        llm_messages,
                        queries,
                        show_bql,
                        resolved.source,
                        reasoning_parts,
                        thinking_parts,
                    )
                    return

                yield StreamEvent('status', {'phase': 'querying'})
                llm_messages.append(self._assistant_message_from_tool_calls(round_result.tool_calls))

                for tool_call in round_result.tool_calls:
                    fn_name = tool_call.name
                    try:
                        fn_args = json.loads(tool_call.arguments or '{}')
                    except json.JSONDecodeError:
                        fn_args = {}

                    tool_start: dict[str, Any] = {'name': fn_name}
                    if fn_name == 'run_bql':
                        tool_start['query'] = fn_args.get('query', '')
                    yield StreamEvent('tool_start', tool_start)

                    thinking_start = format_tool_thinking_start(fn_name, fn_args)
                    if thinking_start:
                        thinking_parts.append(thinking_start)
                        yield StreamEvent('thinking_delta', {'content': thinking_start})

                    queries_before = len(queries)
                    tool_result = self._dispatch_tool(fn_name, fn_args, queries)

                    thinking_end = format_tool_thinking_end(fn_name, tool_result)
                    if thinking_end:
                        thinking_parts.append(thinking_end)
                        yield StreamEvent('thinking_delta', {'content': thinking_end})

                    tool_end: dict[str, Any] = {'name': fn_name}
                    if fn_name == 'run_bql' and len(queries) > queries_before:
                        record = queries[-1]
                        tool_end['bql'] = record.bql
                        tool_end['result_preview'] = record.result_preview
                    yield StreamEvent('tool_end', tool_end)

                    llm_messages.append({
                        'role': 'tool',
                        'tool_call_id': tool_call.id,
                        'content': tool_result,
                    })
                continue

            reply_text = ''.join(round_result.content_parts).strip()
            final = self._build_thinking_reply(
                reply_text, queries, show_bql, resolved.source, reasoning_parts, thinking_parts,
            )
            yield StreamEvent('done', self._done_event_data(final))
            return

    def chat(self, messages: list[dict[str, str]], show_bql: bool = False) -> AssistantReply:
        result: AssistantReply | None = None
        for event in self._iter_chat_events(messages, show_bql=show_bql):
            if event.event == 'done':
                result = AssistantReply(
                    reply=event.data['reply'],
                    queries=[
                        QueryRecord(bql=q['bql'], result_preview=q['result_preview'])
                        for q in event.data['queries']
                    ],
                    api_key_source=event.data['api_key_source'],
                    thinking=event.data.get('thinking', ''),
                    reasoning=event.data.get('reasoning', ''),
                )
        if result is None:
            raise RuntimeError('对话未产生完成事件')
        return result

    def chat_stream(
        self,
        messages: list[dict[str, str]],
        show_bql: bool = False,
    ) -> Iterator[str]:
        try:
            for event in self._iter_chat_events(messages, show_bql=show_bql):
                yield format_sse(event.event, event.data)
        except (ValueError, LedgerNotFoundError):
            raise
        except Exception as exc:
            logger.exception('AI 助手流式调用失败')
            yield format_sse('error', {'detail': f'AI 助手暂时不可用: {exc}'})
