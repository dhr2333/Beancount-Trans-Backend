"""为 LLM 提供账本上下文与 BQL schema 说明。"""
from django.contrib.auth.models import User

from project.apps.translate.models import FormatConfig

from .ledger_query import LedgerQueryService

BQL_SCHEMA_HINT = """
BQL (Bean Query Language) 常用说明：
- 表：默认 postings 视图，字段包括 date, year, month, account, position, payee, narration, tags 等
- 账户匹配：account ~ 'Expenses:Food'  （正则匹配）
- 金额汇总：sum(position) 或 sum(units(position))
- 分组：GROUP BY account, year, month
- 排序：ORDER BY date DESC
- 限制：LIMIT 10
- 日期过滤：year = 2024 AND month = 1，或 date >= 2024-01-01 AND date <= 2024-01-31
- 支出账户通常以 Expenses: 开头，收入以 Income: 开头，资产以 Assets: 开头
"""


def get_ledger_context(user: User) -> str:
    """返回供 LLM 使用的账本上下文文本。"""
    config = FormatConfig.get_user_config(user)
    query_service = LedgerQueryService(user)
    currency = config.currency or 'CNY'

    lines = [
        f'默认货币: {currency}',
        f'账本文件存在: {"是" if query_service.ledger_exists() else "否"}',
        BQL_SCHEMA_HINT.strip(),
    ]

    if query_service.ledger_exists():
        accounts = query_service.list_accounts(limit=100)
        if accounts:
            lines.append('账本账户列表（部分）:')
            lines.extend(f'  - {acc}' for acc in accounts[:80])
            if len(accounts) > 80:
                lines.append(f'  ... 共 {len(accounts)} 个账户')

    return '\n'.join(lines)
