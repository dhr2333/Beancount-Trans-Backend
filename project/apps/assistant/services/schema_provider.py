"""为 LLM 提供账本上下文与 BQL schema 说明。"""
from datetime import date

from django.contrib.auth.models import User

from project.apps.translate.models import FormatConfig

from .bql_reference import build_bql_capability_reference
from .ledger_query import LedgerQueryService
from .metadata_catalog import format_catalog_for_llm
from .reference_date import build_reference_date_context, get_reference_date

BQL_SCHEMA_HINT = """
BQL 速查：默认查询 postings；不要写 FROM / HAVING；账户用 account ~ 正则；
金额汇总用 sum(units(position))；详见下方「BQL 能力说明」。
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
            '本月超过 100 元的大额消费有哪些？',
            f"SELECT date, payee, narration, account, units(position) "
            f"WHERE account ~ '^Expenses' AND year = {year} AND month = {month} "
            f"AND number > 100 ORDER BY date DESC LIMIT 20",
        ),
        (
            '最近 10 笔大额消费（按金额排序）',
            f"SELECT date, payee, narration, account, units(position) "
            f"WHERE account ~ '^Expenses' AND year = {year} AND month = {month} "
            f"ORDER BY units(position) DESC LIMIT 10",
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
        build_bql_capability_reference(),
        build_bql_examples(ref),
    ]

    ledger_accounts: list[str] = []
    if query_service.ledger_exists():
        ledger_accounts = query_service.list_accounts(limit=100)

    lines.append(format_catalog_for_llm(user, ledger_accounts))

    if ledger_accounts:
        lines.append('账本实际出现的账户（部分，BQL 查询范围）:')
        lines.extend(f'  - {acc}' for acc in ledger_accounts[:80])
        if len(ledger_accounts) > 80:
            lines.append(f'  ... 共 {len(ledger_accounts)} 个账户')

    return '\n'.join(lines)
