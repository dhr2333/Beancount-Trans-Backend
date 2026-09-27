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


def ledger_keys_for(item: dict) -> list[str]:
    """共享账本可被 Copilot 接受的 ledger 标识：其别名，或来源用户名。"""
    return list(item.get('aliases') or []) or [item['owner'].username]


def build_ledger_options(shared_ledgers: list[dict] | None) -> list[dict]:
    """构建账本选项列表：首项恒为 self，其后为共享账本（key 取首个可用标识）。"""
    options = [{'key': 'self', 'label': '我的账本'}]
    for item in (shared_ledgers or []):
        keys = ledger_keys_for(item)
        if item.get('aliases'):
            label = f'{keys[0]}（{item["owner"].username}）'
        else:
            label = f'{item["owner"].username} 的账本'
        options.append({
            'key': keys[0],
            'keys': keys,
            'label': label,
        })
    return options


def build_shared_ledger_prompt_block(
    options: list[dict] | None,
    *,
    self_ledger_available: bool = True,
) -> str:
    """生成共享账本说明块；无共享账本时返回空串（保证提示词不变）。"""
    if not options:
        return ''
    shared = [o for o in options if o.get('key') != 'self']
    if not shared:
        return ''
    ledger_lines = []
    for option in options:
        keys = list(option.get('keys') or [option.get('key')])
        label = option.get('label') or option.get('key')
        ledger_lines.append(f'- {label}：可用标识 {"、".join(str(k) for k in keys)}')
    ledger_list = '\n'.join(ledger_lines)
    shared_labels = '」「'.join(
        str(o.get('label') or o.get('key')) for o in shared
    )
    if self_ledger_available:
        prefix_rules = (
            '1. get_ledger_context / run_bql 通过参数 ledger 指定目标账本，缺省 self（我的账本）。\n'
            '2. 默认先查 self；只有在「我的账本不存在」或「对 self 的查询没有返回任何结果/无相关记录」时，'
            '才改用相关的共享账本再查一次。\n'
        )
    else:
        prefix_rules = (
            '1. 「我的账本」当前尚未创建，无法查询；调用 get_ledger_context / run_bql '
            '时必须显式传入 ledger（某个共享账本的可用标识），不要依赖默认的 self。\n'
        )
    rules = prefix_rules + (
        '3. 例外：用户在提问中明确点名了某个可用标识/来源用户（如「老婆的账本里…」），'
        '或明确要求跨账本对比、合计时，直接按需查询对应共享账本，不必先查 self。\n'
        '4. 结论中必须标注每项数字来自哪个账本'
        f'（如「我的账本」「{shared_labels}」）。\n'
        '5. 跨账本合计仅在用户明确要求（如「一共/总共」）时进行；'
        '合计必须说明合计口径，并提示两账本之间的往来/转账可能被重复计入（不要擅自剔除）。\n'
        '6. 共享账本为只读；record_transaction 只能写入我的账本（self）。'
    )
    return (
        '共享账本说明：\n'
        f'当前可访问的账本：\n{ledger_list}\n'
        '每个共享账本可用其「可用标识」（别名）中的任意一个作为 ledger 参数值；'
        '没有别名的共享账本以其来源用户名作为标识。\n'
        '共享账本用于补充本人账本：默认以本人账本为主，只有在下方规则所述的情况下才改用共享账本。\n'
        '规则：\n'
        f'{rules}'
    )


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
            '本月支出科目按金额从高到低排序',
            f"SELECT account, sum(units(position)) WHERE account ~ '^Expenses' "
            f"AND year = {year} AND month = {month} "
            f"GROUP BY account ORDER BY sum(units(position)) DESC",
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
            '本月总收入是多少？',
            f"SELECT sum(units(position)) WHERE account ~ '^Income' "
            f"AND year = {year} AND month = {month}",
        ),
        (
            '本月各收入科目分别是多少？',
            f"SELECT account, sum(units(position)) WHERE account ~ '^Income' "
            f"AND year = {year} AND month = {month} GROUP BY account",
        ),
        (
            '本月工资收入多少？',
            f"SELECT sum(units(position)) WHERE account ~ '^Income:Salary' "
            f"AND year = {year} AND month = {month}",
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
        'Income 的 sum 为负表示收入金额，向用户展示时取绝对值。'
    )
    return '\n'.join(lines).rstrip()


def build_insight_bql_examples(reference_date: date | None = None) -> str:
    """洞察模式专用 BQL few-shot 示例（跨期、payee/link/tag/meta/entries）。"""
    today = reference_date or get_reference_date()
    year, month = today.year, today.month

    examples = [
        (
            '近 6 月每月总支出趋势',
            f"SELECT year, month, sum(units(position)) "
            f"WHERE account ~ '^Expenses' AND year = {year} "
            f"GROUP BY year, month",
        ),
        (
            '公共事业（水电气网物业）各月支出对比',
            f"SELECT year, month, sum(units(position)) "
            f"WHERE account ~ '^Expenses:Home:Utilities' AND year = {year} "
            f"GROUP BY year, month",
        ),
        (
            '某商家过去各月花了多少？',
            "SELECT year, month, sum(units(position)) "
            "WHERE payee ~ '山姆' AND account ~ '^Expenses' "
            f"AND year = {year} GROUP BY year, month",
        ),
        (
            '某 link 关联的所有支出',
            "SELECT date, payee, narration, account, units(position), links "
            "WHERE 'order-001' IN links AND account ~ '^Expenses' "
            "ORDER BY date",
        ),
        (
            '某标签各月支出趋势',
            "SELECT year, month, sum(units(position)) "
            "WHERE '完整标签路径' IN tags AND account ~ '^Expenses' "
            f"AND year = {year} GROUP BY year, month",
        ),
        (
            '本月交易及 time 等 meta 明细',
            f"SELECT date, payee, narration, meta, tags, links "
            f"FROM entries "
            f"WHERE type = 'transaction' AND year = {year} AND month = {month} "
            f"ORDER BY date DESC LIMIT 20",
        ),
        (
            '最近 Balance 与 Pad 对账/补账记录',
            "SELECT date, type, accounts "
            "FROM entries "
            "WHERE type IN ('balance', 'pad') "
            "ORDER BY date DESC LIMIT 20",
        ),
    ]

    lines = [
        '洞察模式 BQL 示例（跨期对比与多维线索追溯；账户/标签路径以平台目录为准）：',
    ]
    for question, bql in examples:
        lines.append(f'【问题】{question}')
        lines.append(f'【BQL】{bql}')
        lines.append('')
    lines.append(
        '说明：发现当期异常线索（突变 payee、罕见 tag、大额 link 等）后，'
        '应再查一条历史/关联查询；meta 从 entries 结果解读，勿在 WHERE 过滤 meta。'
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

    for entry in load_account_catalog(user):
        if not entry.account.startswith('Income:') or not entry.description:
            continue
        if entry.account not in ledger_set:
            continue
        examples.append(
            (
                f'本月{entry.description}收入多少？',
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
