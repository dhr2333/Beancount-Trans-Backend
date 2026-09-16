"""MCP Prompts：面向 MCP 客户端的账本分析提示词模板（用户主动选择）。"""
from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from project.apps.assistant.services.insight_mode import INSIGHT_MODE_BLOCK

INSIGHT_REVIEW_DESCRIPTION = '账本洞察复盘：先跨期对比再追溯线索，输出有数据依据的消费洞察'
MONTHLY_REVIEW_DESCRIPTION = '月度复盘：收入/支出总额、类目结构与环比、大额与异常交易'

_DEFAULT_PERIOD = '最近 3 个月'


def register(server: MCPServer) -> None:
    @server.prompt(
        name='insight_review',
        title='账本洞察复盘',
        description=INSIGHT_REVIEW_DESCRIPTION,
    )
    def insight_review(period: str = '') -> list[dict]:
        scope = (period or '').strip() or _DEFAULT_PERIOD
        text = (
            f'请针对「{scope}」做一次账本洞察复盘。\n\n'
            '工作方式：\n'
            '1. 先调用 get_ledger_context，拿到账户/标签目录与 BQL 用法；\n'
            '2. 用 run_bql 取数：先跨期趋势，再对 1–2 条有故事的线索做追溯；\n'
            '3. 所有数字必须来自查询结果，不要凭印象推断账户名、标签或金额。\n\n'
            f'{INSIGHT_MODE_BLOCK.strip()}'
        )
        return [{'role': 'user', 'content': text}]

    @server.prompt(
        name='monthly_review',
        title='月度复盘',
        description=MONTHLY_REVIEW_DESCRIPTION,
    )
    def monthly_review(period: str = '') -> list[dict]:
        scope = (period or '').strip() or _DEFAULT_PERIOD
        text = (
            f'请对「{scope}」做一次月度复盘。\n\n'
            '工作方式：\n'
            '1. 先调用 get_ledger_context，确认账户/标签目录与默认货币；\n'
            '2. 用 run_bql 依次取数：\n'
            '   - 收入总额（account ~ \'^Income\'）与支出总额（account ~ \'^Expenses\'），算出结余；\n'
            '   - 支出 TOP 类目（GROUP BY account 排序），并与上一期对比；\n'
            '   - 大额单笔与首次出现的 payee；\n'
            '   - 标签维度支出（按需）；\n'
            '3. 数字必须来自查询结果；收入/负债类金额注意复式记账符号，向用户展示时用绝对值。\n\n'
            '输出结构：本期概览（收入/支出/结余）→ 支出类目表 → 2–3 条观察 → 可执行建议。'
        )
        return [{'role': 'user', 'content': text}]
