"""LLM 编排：DeepSeek function calling + BQL 工具。"""
import json
import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from django.conf import settings
from django.contrib.auth.models import User
from openai import OpenAI

from .api_key_resolver import resolve_api_key
from .ledger_query import LedgerNotFoundError, LedgerQueryService
from .reference_date import build_reference_date_context, get_reference_date
from .schema_provider import build_bql_examples, get_ledger_context

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_TEMPLATE = """你是 Beancount-Trans 的个人账本助手。你只能基于工具返回的真实数据回答用户问题。

{reference_date_context}

规则：
1. 回答支出、收入、余额、汇总类问题时，必须先调用 run_bql 执行查询，不要编造数字。
2. 不确定账户名称时，先调用 get_ledger_context 了解账户列表和 BQL 语法。
3. 生成 BQL 时优先模仿下方示例结构；账户用 account ~ 'Expenses' 等正则匹配；金额汇总优先 sum(units(position))。
4. 涉及「本月」「上月」「最近」等时间时，以上述基准日期为准构造 BQL 日期条件。
5. 用中文简洁回答，标明货币单位；若查无数据，明确说明。
6. 同一问题最多调用 run_bql 3 次；若仍无满意结果，请根据已有查询结果作答，不要无限重试。
7. 不要执行写操作，不要讨论与账本无关的话题。

{bql_examples}"""


def build_system_prompt(reference_date: date | None = None) -> str:
    ref = reference_date or get_reference_date()
    return SYSTEM_PROMPT_TEMPLATE.format(
        reference_date_context=build_reference_date_context(ref),
        bql_examples=build_bql_examples(ref),
    )

TOOLS = [
    {
        'type': 'function',
        'function': {
            'name': 'get_ledger_context',
            'description': '获取用户账本上下文：账户列表、默认货币、BQL 语法说明与查询示例',
            'parameters': {'type': 'object', 'properties': {}, 'required': []},
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'run_bql',
            'description': (
                '执行只读 BQL 查询并返回表格结果。必须 SELECT 开头；'
                '账户用 account ~ 正则匹配；时间用 year/month 或 date 范围；'
                '优先模仿 system prompt 中的 BQL 示例结构。'
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
            except Exception as exc:
                return f'查询失败: {exc}'

        return f'未知工具: {name}'

    def _finalize_reply(
        self,
        reply_text: str,
        queries: list[QueryRecord],
        show_bql: bool,
        api_key_source: str,
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
        )

    def _force_final_reply(
        self,
        client: OpenAI,
        llm_messages: list[dict[str, Any]],
        queries: list[QueryRecord],
        show_bql: bool,
        api_key_source: str,
    ) -> AssistantReply:
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
        response = client.chat.completions.create(
            model=self.model,
            messages=synthesis_messages,
            temperature=0.1,
        )
        reply_text = (response.choices[0].message.content or '').strip()
        return self._finalize_reply(reply_text, queries, show_bql, api_key_source)

    def chat(self, messages: list[dict[str, str]], show_bql: bool = False) -> AssistantReply:
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

        tool_round = 0
        while True:
            response = client.chat.completions.create(
                model=self.model,
                messages=llm_messages,
                tools=TOOLS,
                tool_choice='auto',
                temperature=0.1,
            )
            choice = response.choices[0]
            message = choice.message

            if choice.finish_reason == 'tool_calls' or message.tool_calls:
                tool_round += 1
                if tool_round > self.MAX_TOOL_ROUNDS:
                    return self._force_final_reply(
                        client,
                        llm_messages,
                        queries,
                        show_bql,
                        resolved.source,
                    )
                llm_messages.append(message.model_dump(exclude_none=True))
                for tool_call in message.tool_calls or []:
                    fn_name = tool_call.function.name
                    try:
                        fn_args = json.loads(tool_call.function.arguments or '{}')
                    except json.JSONDecodeError:
                        fn_args = {}
                    tool_result = self._dispatch_tool(fn_name, fn_args, queries)
                    llm_messages.append({
                        'role': 'tool',
                        'tool_call_id': tool_call.id,
                        'content': tool_result,
                    })
                continue

            reply_text = (message.content or '').strip()
            return self._finalize_reply(reply_text, queries, show_bql, resolved.source)
