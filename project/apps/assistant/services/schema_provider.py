"""为 LLM 提供账本上下文与 BQL schema 说明。"""
from datetime import date

from django.contrib.auth.models import User

from project.apps.translate.models import FormatConfig

from .ledger_query import LedgerQueryService
from .reference_date import build_reference_date_context, get_reference_date

BQL_SCHEMA_HINT = """
BQL (Bean Query Language) 常用说明：
- 默认查询 postings 视图，字段包括 date, year, month, account, position, payee, narration, tags 等
- 不要写 FROM 子句
- 账户匹配：优先 account ~ 'Expenses' 或 account ~ '^Expenses'（正则），避免臆造不存在的精确账户名
- 金额汇总：优先 sum(units(position))；有 cost/lot 时避免直接 sum(position) 导致难读结果
- 分组：GROUP BY account, year, month, payee
- 排序：ORDER BY date DESC
- 限制：LIMIT 10
- 日期过滤：year = YYYY AND month = M，或 date >= YYYY-MM-DD AND date <= YYYY-MM-DD
- 相对时间请以「基准日期」段落为准展开，不要使用中文字面量
- 支出账户通常以 Expenses: 开头，收入以 Income: 开头，资产以 Assets: 开头
- 查询失败或返回 (无结果) 时：最多再试 1 次，换更宽账户前缀或检查年月，不要连续多次微调相似语句
"""


def _last_month(reference_date: date) -> tuple[int, int]:
    if reference_date.month == 1:
        return reference_date.year - 1, 12
    return reference_date.year, reference_date.month - 1


def build_bql_examples(reference_date: date | None = None) -> str:
    """生成与基准日期联动的 BQL few-shot 示例。"""
    today = reference_date or get_reference_date()
    year, month = today.year, today.month
    last_year, last_month = _last_month(today)

    examples = [
        (
            '本月总支出是多少？',
            f"SELECT sum(units(position)) WHERE account ~ '^Expenses' "
            f"AND year = {year} AND month = {month}",
        ),
        (
            '本月各支出科目花了多少？',
            f"SELECT account, sum(units(position)) WHERE account ~ '^Expenses' "
            f"AND year = {year} AND month = {month} GROUP BY account",
        ),
        (
            '上个月总支出是多少？',
            f"SELECT sum(units(position)) WHERE account ~ '^Expenses' "
            f"AND year = {last_year} AND month = {last_month}",
        ),
        (
            '最近 10 笔大额消费有哪些？',
            "SELECT date, payee, narration, account, units(position) "
            "WHERE account ~ '^Expenses' ORDER BY date DESC LIMIT 10",
        ),
        (
            '本月按商家汇总支出',
            f"SELECT payee, sum(units(position)) WHERE account ~ '^Expenses' "
            f"AND year = {year} AND month = {month} GROUP BY payee",
        ),
        (
            '各资产账户入账汇总（postings 汇总，非 Fava 余额）',
            "SELECT account, sum(units(position)) WHERE account ~ '^Assets' GROUP BY account",
        ),
    ]

    lines = ['BQL 查询示例（请模仿结构，账户名以账本账户列表为准）：']
    for question, bql in examples:
        lines.append(f'【问题】{question}')
        lines.append(f'【BQL】{bql}')
        lines.append('')
    return '\n'.join(lines).rstrip()


def get_ledger_context(user: User, reference_date: date | None = None) -> str:
    """返回供 LLM 使用的账本上下文文本。"""
    ref = reference_date or get_reference_date()
    config = FormatConfig.get_user_config(user)
    query_service = LedgerQueryService(user)
    currency = config.currency or 'CNY'

    lines = [
        build_reference_date_context(ref),
        f'默认货币: {currency}',
        f'账本文件存在: {"是" if query_service.ledger_exists() else "否"}',
        BQL_SCHEMA_HINT.strip(),
        build_bql_examples(ref),
    ]

    if query_service.ledger_exists():
        accounts = query_service.list_accounts(limit=100)
        if accounts:
            lines.append('账本账户列表（部分）:')
            lines.extend(f'  - {acc}' for acc in accounts[:80])
            if len(accounts) > 80:
                lines.append(f'  ... 共 {len(accounts)} 个账户')

    return '\n'.join(lines)
