"""为 LLM 提供账本上下文与 BQL schema 说明。"""
from datetime import date

from django.contrib.auth.models import User

from project.apps.translate.models import FormatConfig

from .bql_reference import build_bql_capability_reference
from .ledger_query import LedgerQueryService
from .metadata_catalog import format_catalog_for_llm, load_account_catalog, load_tag_catalog
from .reference_date import build_reference_date_context, get_reference_date

BQL_SCHEMA_HINT = """
BQL 速查：默认查询 postings；不要写 FROM / HAVING；账户用 account ~ 正则；
金额汇总用 sum(units(position))；详见下方「BQL 能力说明」。
"""


def _last_month(reference_date: date) -> tuple[int, int]:
    if reference_date.month == 1:
        return reference_date.year - 1, 12
    return reference_date.year, reference_date.month - 1


def _find_receivable_prefix(ledger_accounts: list[str]) -> str | None:
    for acc in sorted(ledger_accounts):
        parts = acc.split(':')
        for i, part in enumerate(parts):
            if 'receivable' in part.lower():
                return ':'.join(parts[: i + 1])
    return None


def build_bql_examples(reference_date: date | None = None) -> str:
    """生成与基准日期联动的通用 BQL few-shot 示例（仅顶层账户类型）。"""
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
            '本月餐饮（含子科目）总支出？',
            f"SELECT sum(units(position)) WHERE account ~ '^Expenses:Food' "
            f"AND year = {year} AND month = {month}",
        ),
        (
            '本月餐饮各子科目分别花了多少？',
            f"SELECT account, sum(units(position)) WHERE account ~ '^Expenses:Food' "
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
            '各资产账户累计余额（postings 汇总）',
            "SELECT account, sum(units(position)) WHERE account ~ '^Assets' GROUP BY account",
        ),
        (
            '各负债账户欠款多少？',
            "SELECT account, sum(units(position)) WHERE account ~ '^Liabilities' GROUP BY account",
        ),
        (
            '某资产子账户余额是多少？',
            "SELECT sum(units(position)) WHERE account ~ '^Assets:...'",
        ),
        (
            '某标签本月支出花了多少？',
            f"SELECT sum(units(position)) WHERE '完整标签路径' IN tags "
            f"AND account ~ '^Expenses' AND year = {year} AND month = {month}",
        ),
        (
            '某标签下的交易明细',
            "SELECT date, payee, narration, account, units(position) "
            "WHERE '完整标签路径' IN tags ORDER BY date DESC LIMIT 20",
        ),
    ]

    lines = [
        'BQL 查询示例（请模仿结构；子账户与标签路径以平台目录 / 账本账户列表为准）：',
    ]
    for question, bql in examples:
        lines.append(f'【问题】{question}')
        lines.append(f'【BQL】{bql}')
        lines.append('')
    lines.append(
        '说明：余额查询若 sum 列为空白，表示余额为 0（与 Fava 一致）。'
        'GROUP BY 时父账户行仅含直接 posting，不是子树总额；无 posting 的账户不会出现。'
    )
    return '\n'.join(lines).rstrip()


def build_user_specific_bql_examples(
    user: User,
    reference_date: date | None = None,
    ledger_accounts: list[str] | None = None,
) -> str:
    """基于用户账户/标签目录生成贴近语义的 BQL 示例（仅 get_ledger_context）。"""
    ref = reference_date or get_reference_date()
    year, month = ref.year, ref.month
    ledger_set = set(ledger_accounts or [])
    examples: list[tuple[str, str]] = []

    for entry in load_account_catalog(user):
        if entry.account not in ledger_set:
            continue
        if entry.account_type == '资产账户' and entry.description:
            label = entry.description
            examples.append(
                (
                    f'{label}余额是多少？',
                    f"SELECT sum(units(position)) WHERE account ~ '^{entry.account}'",
                )
            )
            break

    for entry in load_account_catalog(user):
        if not entry.account.startswith('Expenses:') or not entry.description:
            continue
        if entry.account not in ledger_set:
            continue
        examples.append(
            (
                f'本月{entry.description}花了多少？',
                f"SELECT sum(units(position)) WHERE account ~ '^{entry.account}' "
                f"AND year = {year} AND month = {month}",
            )
        )
        break

    receivable_prefix = _find_receivable_prefix(list(ledger_set))
    if receivable_prefix:
        examples.append(
            (
                '各应收款账户余额是多少？',
                f"SELECT account, sum(units(position)) WHERE account ~ '^{receivable_prefix}' "
                f"GROUP BY account",
            )
        )

    tag_entries = load_tag_catalog(user)
    if tag_entries:
        tag = tag_entries[0]
        label = tag.description or tag.full_path.split('/')[-1]
        examples.append(
            (
                f'本月{label}相关支出？',
                f"SELECT sum(units(position)) WHERE '{tag.full_path}' IN tags "
                f"AND account ~ '^Expenses' AND year = {year} AND month = {month}",
            )
        )

    if not examples:
        return ''

    lines = [
        '账本相关 BQL 示例（账户/标签来自你的目录，可直接参考；'
        '支出类目总额含子科目，用前缀 account ~ 的 sum）：',
    ]
    for question, bql in examples[:3]:
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

    user_examples = build_user_specific_bql_examples(
        user, reference_date=ref, ledger_accounts=ledger_accounts
    )
    if user_examples:
        lines.append(user_examples)

    lines.append(format_catalog_for_llm(user, ledger_accounts))

    if ledger_accounts:
        lines.append('账本实际出现的账户（部分，BQL 查询范围）:')
        lines.extend(f'  - {acc}' for acc in ledger_accounts[:80])
        if len(ledger_accounts) > 80:
            lines.append(f'  ... 共 {len(ledger_accounts)} 个账户')

    return '\n'.join(lines)
