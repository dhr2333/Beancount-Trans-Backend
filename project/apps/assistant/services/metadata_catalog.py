"""平台账户与标签描述目录，供 LLM 语义映射。"""
from dataclasses import dataclass

from django.contrib.auth.models import User

from project.apps.account.models import Account
from project.apps.tags.models import Tag

TAG_DESCRIPTION_MAX_LEN = 80


@dataclass(frozen=True)
class AccountCatalogEntry:
    account: str
    description: str
    account_type: str


@dataclass(frozen=True)
class TagCatalogEntry:
    full_path: str
    description: str


def _account_type(account_path: str) -> str:
    root = account_path.split(':')[0] if account_path else ''
    mapping = {
        'Assets': '资产账户',
        'Liabilities': '负债账户',
        'Equity': '权益账户',
        'Income': '收入账户',
        'Expenses': '支出账户',
    }
    return mapping.get(root, '未知类型')


def load_account_catalog(user: User) -> list[AccountCatalogEntry]:
    entries = []
    for row in Account.objects.filter(owner=user, enable=True).order_by('account').values(
        'account', 'description'
    ):
        account = row['account']
        entries.append(
            AccountCatalogEntry(
                account=account,
                description=(row['description'] or '').strip(),
                account_type=_account_type(account),
            )
        )
    return entries


def load_tag_catalog(user: User) -> list[TagCatalogEntry]:
    entries = []
    for tag in Tag.objects.filter(owner=user, enable=True).order_by('name'):
        entries.append(
            TagCatalogEntry(
                full_path=tag.get_full_path(),
                description=(tag.description or '').strip(),
            )
        )
    return entries


def build_path_to_description_map(user: User) -> dict[str, str]:
    """账户路径 → 非空描述，供 BQL 结果富化。"""
    return {
        entry.account: entry.description
        for entry in load_account_catalog(user)
        if entry.description
    }


def _format_description_label(description: str) -> str:
    if description:
        return description
    return '（无描述）'


def _truncate_tag_description(description: str) -> str:
    if len(description) <= TAG_DESCRIPTION_MAX_LEN:
        return description
    return description[: TAG_DESCRIPTION_MAX_LEN - 1] + '…'


def _should_include_account(
    entry: AccountCatalogEntry,
    ledger_account_set: set[str],
) -> bool:
    if entry.account.startswith('Expenses:'):
        return True
    if entry.description:
        return True
    return entry.account in ledger_account_set


def format_catalog_for_llm(
    user: User,
    ledger_accounts: list[str] | None = None,
) -> str:
    """生成平台账户/标签目录文本。"""
    ledger_set = set(ledger_accounts or [])
    account_entries = [
        e for e in load_account_catalog(user)
        if _should_include_account(e, ledger_set)
    ]
    tag_entries = load_tag_catalog(user)

    lines: list[str] = []

    lines.append('平台账户目录（路径 → 描述，用于理解用户说的类别名称）:')
    if account_entries:
        for entry in account_entries:
            label = _format_description_label(entry.description)
            lines.append(f'  {entry.account} → {label}')
    else:
        lines.append('  （暂无已启用账户）')

    lines.append('')
    lines.append('平台标签目录（路径 → 描述，用于按标签筛选）:')
    if tag_entries:
        for entry in tag_entries:
            desc = _truncate_tag_description(_format_description_label(entry.description))
            lines.append(f'  {entry.full_path} → {desc}')
    else:
        lines.append('  （暂无已启用标签）')

    lines.append('')
    lines.append(
        '说明：BQL 只能查询账本文件中实际存在的 posting；'
        '上述目录用于将用户自然语言类别映射到 account ~ / tags ~ 条件。'
    )

    return '\n'.join(lines)
