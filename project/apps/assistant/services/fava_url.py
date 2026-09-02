"""为 Copilot 查询结果拼装 Fava 深链相对路径（不含可变 uuid 前缀）。"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote, urlencode

from django.conf import settings
from django.contrib.auth.models import User

from project.apps.fava_instances.models import FavaInstance
from project.utils.fava_static import parse_fava_static_user_map, resolve_static_fava_url
from project.utils.file import BeanFileManager

DETAIL_FILTER_PATTERN = re.compile(
    r'\b(payee|narration|id|links|filename|lineno|location)\s*(=|~|LIKE|IN)\b',
    re.IGNORECASE,
)
ACCOUNT_ROOT_PATTERN = re.compile(
    r"account\s*~\s*['\"]?\^?(Income|Expenses|Assets|Liabilities|Equity)",
    re.IGNORECASE,
)
ACCOUNT_EQ_PATTERN = re.compile(
    r"account\s*=\s*['\"]?(Income|Expenses|Assets|Liabilities|Equity)",
    re.IGNORECASE,
)


def slugify_title(title: str) -> str:
    """对齐 Fava application._slug：NFKC、去非词字符、lower、空白变连字符，保留中文。"""
    normalized = unicodedata.normalize('NFKC', title or '')
    cleaned = re.sub(r'[^\w\s-]', '', normalized, flags=re.UNICODE).strip().lower()
    slug = re.sub(r'[-\s]+', '-', cleaned)
    return slug or 'ledger'


def read_ledger_title(user: User) -> str:
    path = BeanFileManager.get_main_bean_path(user)
    try:
        with open(path, encoding='utf-8') as handle:
            for line in handle:
                match = re.match(r'^\s*option\s+"title"\s+"(.*)"\s*$', line)
                if match:
                    return match.group(1)
    except OSError:
        pass
    username = getattr(user, 'username', '') or 'user'
    return f'{username}的账本'


def get_or_create_fava_instance_uuid(user: User) -> str:
    """仅 get_or_create 实例以取得稳定 uuid，不启动容器。"""
    instance, _ = FavaInstance.objects.get_or_create(
        owner=user,
        defaults={'status': 'stopped'},
    )
    return str(instance.uuid)


def fava_prefix_for_user(user: User) -> str | None:
    deploy_mode = getattr(settings, 'FAVA_DEPLOY_MODE', 'dynamic')
    if deploy_mode == 'static':
        raw_map = getattr(settings, 'FAVA_STATIC_USER_MAP', '')
        if isinstance(raw_map, dict):
            mapping = raw_map
        else:
            mapping = parse_fava_static_user_map(str(raw_map or ''))
        url = resolve_static_fava_url(user, mapping)
        return url.rstrip('/') if url else None
    uuid = get_or_create_fava_instance_uuid(user)
    return f'/{uuid}'


def build_relative_path(slug: str, report: str, params: dict[str, str]) -> str:
    query = urlencode(params, quote_via=quote)
    if query:
        return f'{slug}/{report}/?{query}'
    return f'{slug}/{report}/'


def build_query_path(user: User, bql: str, *, slug: str | None = None) -> str:
    ledger_slug = slug or slugify_title(read_ledger_title(user))
    return build_relative_path(ledger_slug, 'query', {'query_string': bql})


def parse_fava_time_param(bql: str) -> str | None:
    year_match = re.search(r'\byear\s*=\s*(\d{4})\b', bql, re.IGNORECASE)
    if year_match:
        return year_match.group(1)

    year_start = re.search(r"date\s*>=\s*['\"]?(\d{4})-01-01", bql, re.IGNORECASE)
    if year_start:
        year = year_start.group(1)
        if re.search(rf"date\s*<=\s*['\"]?{year}-12-31", bql, re.IGNORECASE):
            return year

    month_start = re.search(r"date\s*>=\s*['\"]?(\d{4}-\d{2})-\d{2}", bql, re.IGNORECASE)
    if month_start:
        month_prefix = month_start.group(1)
        if re.search(rf"date\s*<=\s*['\"]?{re.escape(month_prefix)}-\d{{2}}", bql, re.IGNORECASE):
            return month_prefix

    return None


def detect_account_roots(bql: str) -> set[str]:
    roots: set[str] = set()
    for pattern in (ACCOUNT_ROOT_PATTERN, ACCOUNT_EQ_PATTERN):
        for match in pattern.finditer(bql):
            roots.add(match.group(1).capitalize())
    return roots


def is_aggregate_query(bql: str) -> bool:
    upper = bql.upper()
    if 'GROUP BY' in upper:
        return True
    if re.search(r'\bsum\s*\(', bql, re.IGNORECASE):
        if not re.search(r'\bdate\s*,', bql, re.IGNORECASE):
            return True
    return False


def infer_report_link(user: User, bql: str, *, slug: str | None = None) -> dict[str, str] | None:
    if DETAIL_FILTER_PATTERN.search(bql):
        return None
    if not is_aggregate_query(bql):
        return None

    time_param = parse_fava_time_param(bql)
    if not time_param:
        return None

    roots = detect_account_roots(bql)
    ledger_slug = slug or slugify_title(read_ledger_title(user))

    if roots & {'Income', 'Expenses'}:
        name = 'income_statement'
        label = f'{time_param} 损益表'
        return {
            'name': name,
            'label': label,
            'path': build_relative_path(ledger_slug, name, {'time': time_param}),
        }

    if roots & {'Assets', 'Liabilities', 'Equity'}:
        name = 'balance_sheet'
        label = f'{time_param} 资产负债表'
        return {
            'name': name,
            'label': label,
            'path': build_relative_path(ledger_slug, name, {'time': time_param}),
        }

    return None


@dataclass
class QueryFavaLinks:
    fava_path: str
    report: dict[str, str] | None = None


def build_query_fava_links(user: User, bql: str) -> QueryFavaLinks:
    ledger_slug = slugify_title(read_ledger_title(user))
    query_path = build_query_path(user, bql, slug=ledger_slug)
    report = infer_report_link(user, bql, slug=ledger_slug)
    return QueryFavaLinks(fava_path=query_path, report=report)


def query_record_fava_fields(user: User, bql: str) -> dict[str, Any]:
    links = build_query_fava_links(user, bql)
    payload: dict[str, Any] = {'fava_path': links.fava_path}
    if links.report:
        payload['report'] = links.report
    return payload
