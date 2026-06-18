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
from .reply_number_guard import (
    GUARD_DISCLAIMER,
    GUARD_RETRY_MESSAGE,
    apply_guard_disclaimer,
    validate_reply_numbers,
)
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
1. 凡涉及金额、余额、占比、合计、排名、对比的回答（含「分析 / 详细 / 结构 / 明细」），必须先调用 run_bql；不得仅凭 get_ledger_context 中的账户名作答，不要编造数字。
2. 禁止心算：不得对 BQL 返回的多行明细或账户列表手动加减乘除；多账户合计、余额、总额必须用 sum(units(position)) 与 GROUP BY（或单次 sum）由查询引擎计算。
3. 应收款、资产、负债、收入等：先对照平台账户目录映射 account ~ 正则（如 ^Assets:Receivable），再用 GROUP BY account 查各户余额；需要总额时用 sum(units(position))。
4. 不确定账户名称时，先调用 get_ledger_context 了解平台账户/标签目录、账本账户列表和 BQL 语法。
5. 用户提及支出/收入类别（如「餐饮」「交通」）时，先对照「平台账户目录」描述匹配，再写 account ~ 正则（子科目用 ^Expenses:Food 等形式）。
6. 涉及消费性质（必要/非必要、线上/线下等）时，对照「平台标签目录」，BQL 用 '完整标签路径' IN tags 筛选。
7. 展示结果时：有平台描述则写「描述（账户路径）」；无描述则用账户路径；表格汇总同样遵循。
8. 生成 BQL 时严格遵守「BQL 能力说明」与下方示例；账户用 account ~ 正则；金额过滤用 number 列，禁止 units(position) > N。
9. 结构/明细分析：先用聚合查询（GROUP BY account 或 payee）定位重点，再可选第二条明细查询；若结果提示「已截断」，必须改用 GROUP BY 聚合重查，禁止对截断样本求和。
10. 涉及「本月」「上月」「最近」等时间时，以上述基准日期为准构造 BQL 日期条件。
11. 用中文简洁回答，优先使用 Markdown 结构化展示，标明货币单位；若查无数据，明确说明。
12. 同一问题最多调用 run_bql 3 次；若仍无满意结果，请根据已有查询结果作答，不要无限重试。
13. 不要执行写操作，不要讨论与账本无关的话题。
14. 使用 Markdown 格式化回答：金额与关键数字用 **粗体**；多项对比用 Markdown 表格；列举用有序/无序列表；不要输出原始 HTML。
15. 调用工具前，用一两句话简要说明你的分析思路（会展示在「思考过程」中）；最终回答中不要重复这段思路。

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
                '分析/余额/合计/对比类问题必须用 sum(units(position)) 与 GROUP BY 聚合，禁止拉明细后心算；'
                '用户说的类别名称先对照平台账户/标签目录映射到 account ~ / \'标签路径\' IN tags；'
                '账户用 account ~ 正则；时间用 year/month 或 date 范围；'
                '金额过滤用 number > N，禁止 units(position) > N；'
                '结果截断时改用 GROUP BY 重查；遵守 system prompt 中的 BQL 能力说明与示例。'
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
        api_reasoning_parts: list[str],
        planning_parts: list[str],
        thinking_parts: list[str],
    ) -> AssistantReply:
        reasoning_text = self._merged_reasoning_text(api_reasoning_parts, planning_parts)
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
        planning_mode: bool = False,
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
                    yield StreamEvent('reasoning_delta', {
                        'content': reasoning_content,
                        'source': 'api',
                    })
            if delta.content:
                content_parts.append(delta.content)
                if stream_text:
                    if planning_mode:
                        yield StreamEvent('reasoning_delta', {
                            'content': delta.content,
                            'source': 'planning',
                        })
                    elif not tool_calls_map:
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
        api_reasoning_parts: list[str],
        planning_parts: list[str],
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
                    source = item.data.get('source', 'api')
                    if source == 'planning':
                        planning_parts.append(item.data['content'])
                    else:
                        api_reasoning_parts.append(item.data['content'])
                yield item
            else:
                content_parts = item.content_parts

        reply_text = ''.join(content_parts).strip()
        final = self._build_thinking_reply(
            reply_text,
            queries,
            show_bql,
            api_key_source,
            api_reasoning_parts,
            planning_parts,
            thinking_parts,
        )
        yield from self._yield_validated_final(
            client,
            llm_messages,
            final,
            show_bql,
            api_reasoning_parts,
            planning_parts,
            thinking_parts,
        )

    def _merged_reasoning_text(
        self,
        api_reasoning_parts: list[str],
        planning_parts: list[str],
    ) -> str:
        api_text = ''.join(api_reasoning_parts).strip()
        planning_text = ''.join(planning_parts).strip()
        if api_text and planning_text:
            return f'{api_text}\n\n{planning_text}'
        return api_text or planning_text

    def _yield_validated_final(
        self,
        client: OpenAI,
        llm_messages: list[dict[str, Any]],
        final: AssistantReply,
        show_bql: bool,
        api_reasoning_parts: list[str],
        planning_parts: list[str],
        thinking_parts: list[str],
    ) -> Iterator[StreamEvent]:
        validation = validate_reply_numbers(final.reply, final.queries)
        if validation.ok:
            yield StreamEvent('done', self._done_event_data(final))
            return

        synthesis_messages = [
                *llm_messages,
                {'role': 'assistant', 'content': final.reply},
                {'role': 'user', 'content': GUARD_RETRY_MESSAGE},
        ]
        yield StreamEvent('status', {'phase': 'writing'})
        content_parts: list[str] = []
        for item in self._run_llm_round(client, synthesis_messages, stream_text=True):
            if isinstance(item, StreamEvent):
                yield item
            else:
                content_parts = item.content_parts

        reply_text = ''.join(content_parts).strip()
        final = self._build_thinking_reply(
            reply_text,
            final.queries,
            show_bql,
            final.api_key_source,
            api_reasoning_parts,
            planning_parts,
            thinking_parts,
        )
        validation = validate_reply_numbers(final.reply, final.queries)

        if not validation.ok:
            base_reply = final.reply.split(GUARD_DISCLAIMER.strip())[0].rstrip()
            final = self._finalize_reply(
                apply_guard_disclaimer(base_reply),
                final.queries,
                show_bql,
                final.api_key_source,
                reasoning=final.reasoning,
                thinking=final.thinking,
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
        api_reasoning_parts: list[str] = []
        planning_parts: list[str] = []
        thinking_parts: list[str] = []

        while True:
            round_result: _StreamRoundResult | None = None
            writing_status_sent = False
            planning_len_before = len(planning_parts)
            for item in self._run_llm_round(
                client,
                llm_messages,
                tools=TOOLS,
                tool_choice='auto',
                stream_text=True,
                planning_mode=True,
            ):
                if isinstance(item, StreamEvent):
                    if item.event == 'reasoning_delta':
                        source = item.data.get('source', 'api')
                        if source == 'planning':
                            planning_parts.append(item.data['content'])
                        else:
                            api_reasoning_parts.append(item.data['content'])
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
                        api_reasoning_parts,
                        planning_parts,
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

            planning_parts[planning_len_before:] = []
            merged_thinking = merge_thinking_text(
                self._merged_reasoning_text(api_reasoning_parts, planning_parts),
                ''.join(thinking_parts),
            )
            if merged_thinking.strip():
                yield StreamEvent('thinking_set', {
                    'content': merged_thinking,
                    'reasoning': self._merged_reasoning_text(api_reasoning_parts, planning_parts),
                })

            yield StreamEvent('status', {'phase': 'writing'})
            for piece in round_result.content_parts:
                yield StreamEvent('delta', {'content': piece})

            reply_text = ''.join(round_result.content_parts).strip()
            final = self._build_thinking_reply(
                reply_text,
                queries,
                show_bql,
                resolved.source,
                api_reasoning_parts,
                planning_parts,
                thinking_parts,
            )
            yield from self._yield_validated_final(
                client,
                llm_messages,
                final,
                show_bql,
                api_reasoning_parts,
                planning_parts,
                thinking_parts,
            )
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
