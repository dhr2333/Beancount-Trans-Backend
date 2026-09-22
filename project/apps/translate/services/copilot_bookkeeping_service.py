# project/apps/translate/services/copilot_bookkeeping_service.py
"""
Copilot 记账条目暂存区服务

把 Copilot（LLM）给出的结构化交易（支出 / 收入 / 转账）转成与账单解析一致的
Beancount 条目，写入用户级暂存区（复用 ParseReviewService，缓存键
``parse_result:copilot:{user_id}``），再并入统一审核队列并激活 entry_review 待办。

本服务不写任何账本文件，条目写入交由审核确认 / 到期自动写入链路。
"""
import logging
import re
import time
import uuid as uuid_lib
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from django.conf import settings
from django.utils import timezone

from project.apps.account.models import Account
from project.apps.tags.models import Tag
from project.apps.translate.services.entry_dedup_service import EntryDedupService
from project.apps.translate.services.entry_review_queue_service import (
    EntryReviewQueueService,
)
from project.apps.translate.services.parse_review_service import ParseReviewService
from project.apps.translate.utils import FormatData
from project.apps.translate.utils.beancount_validator import BeancountValidator
from project.utils.tools import get_user_config

logger = logging.getLogger(__name__)

_DATE_PATTERN = re.compile(r'^\d{4}-\d{2}-\d{2}$')

ENTRY_TYPES = ('expense', 'income', 'transfer')

# 入参 type -> original_row.transaction_type（与账单解析的收支方向保持一致）
_ORIGINAL_ROW_TX_TYPES = {'expense': '支出', 'income': '收入', 'transfer': '/'}
_TYPE_LABELS = {'expense': '支出', 'income': '收入', 'transfer': '转账'}

_ACCOUNT_MISSING_MESSAGE = (
    '账户不在用户账户目录中，请先调用 get_ledger_context 核对或询问用户'
)


class CopilotBookkeepingService:
    """Copilot 记账条目暂存区服务（全 classmethod）"""

    SOURCE = 'copilot'
    SOURCE_LABEL = 'Copilot 记账'
    DEFAULT_MAX_ENTRIES = 10

    # ------------------------------------------------------------------
    # 暂存区基础读写（缓存键 parse_result:copilot:{user_id}）
    # ------------------------------------------------------------------
    @classmethod
    def staging_key(cls, user_id) -> str:
        """暂存区标识，作为 ParseReviewService 的 file_id 参数使用。"""
        return f'{cls.SOURCE}:{user_id}'

    @classmethod
    def get_staging_data(cls, user_id) -> Optional[Dict[str, Any]]:
        """读取暂存区原始数据（不存在返回 None）。"""
        return ParseReviewService.get_parse_result(cls.staging_key(user_id))

    @classmethod
    def has_staging(cls, user_id) -> bool:
        """用户是否存在 Copilot 记账暂存区。"""
        return cls.get_staging_data(user_id) is not None

    @classmethod
    def expires_at(cls, user_id) -> Optional[float]:
        """暂存区审核截止时间（Unix 时间戳，秒）。"""
        return ParseReviewService.get_review_expires_at(
            cls.get_staging_data(user_id), None
        )

    @classmethod
    def source_ref(cls, entry_uuid: str) -> Dict[str, Any]:
        """统一审核队列引用（copilot 来源没有 file_id）。"""
        return {'source': cls.SOURCE, 'file_id': None, 'uuid': entry_uuid}

    @classmethod
    def list_entries(cls, user_id) -> List[Dict[str, Any]]:
        """按暂存区顺序返回条目副本，并补充来源字段。"""
        data = cls.get_staging_data(user_id) or {}
        entries: List[Dict[str, Any]] = []
        for entry in data.get('formatted_data') or []:
            # 复制条目，避免调用方修改污染 Redis 缓存中的结构
            item = dict(entry)
            item['source'] = cls.SOURCE
            item['file_id'] = None
            item['file_name'] = cls.SOURCE_LABEL
            entries.append(item)
        return entries

    @classmethod
    def get_entry(cls, user_id, entry_uuid: str) -> Optional[Dict[str, Any]]:
        """按 uuid 取单条条目（副本）。"""
        for entry in cls.list_entries(user_id):
            if entry.get('uuid') == entry_uuid:
                return entry
        return None

    @classmethod
    def remove_entries(cls, user_id, uuids: List[str]) -> bool:
        """从暂存区移除指定 uuid 的条目。"""
        return ParseReviewService.remove_entries(cls.staging_key(user_id), uuids)

    @classmethod
    def clear(cls, user_id) -> bool:
        """删除整个暂存区。"""
        return ParseReviewService.delete_parse_result(cls.staging_key(user_id))

    # ------------------------------------------------------------------
    # 校验辅助
    # ------------------------------------------------------------------
    @classmethod
    def max_entries(cls) -> int:
        """单次可提交的最大条数。"""
        return int(
            getattr(settings, 'COPILOT_BOOKKEEPING_MAX_ENTRIES', cls.DEFAULT_MAX_ENTRIES)
        )

    @classmethod
    def _staging_count(cls, user_id) -> int:
        data = cls.get_staging_data(user_id) or {}
        return len(data.get('formatted_data') or [])

    @classmethod
    def _account_exists(cls, user, account_path: str) -> bool:
        if not account_path:
            return False
        return Account.objects.filter(
            owner=user, enable=True, account=account_path
        ).exists()

    @classmethod
    def _enabled_tag_paths(cls, user) -> Set[str]:
        """用户启用的标签完整路径集合。"""
        return {
            tag.get_full_path()
            for tag in Tag.objects.filter(owner=user, enable=True)
        }

    @classmethod
    def _escape_text(cls, text: str) -> str:
        """转义引号并折叠换行，避免破坏 Beancount 首行。"""
        return ' '.join(str(text).replace('"', '\\"').split())

    # ------------------------------------------------------------------
    # 条目构建
    # ------------------------------------------------------------------
    @classmethod
    def _normalize_tags(cls, raw_tags, tag_paths: Set[str]):
        """校验并规范化标签（允许带或不带 # 前缀），返回 (paths, error)。"""
        if raw_tags is None:
            return [], None
        if not isinstance(raw_tags, list):
            return None, 'tags 必须是数组'

        paths: List[str] = []
        for item in raw_tags:
            path = str(item or '').strip().lstrip('#')
            if not path:
                continue
            if path not in tag_paths:
                return None, f'标签不存在于用户标签目录: {path}'
            if path not in paths:
                paths.append(path)
        return paths, None

    @classmethod
    def _format_transfer(
        cls,
        *,
        date: str,
        config,
        payee: str,
        narration: str,
        tag_text: Optional[str],
        entry_time: str,
        entry_uuid: str,
        status: str,
        from_account: str,
        to_account: str,
        amount: str,
        currency: str,
    ) -> str:
        """转账条目：与 FormatData 一致的头部与元数据 + 两条资产 posting。"""
        header = f'{date} {getattr(config, "flag", "*")} "{payee}"'
        if getattr(config, 'show_note', True):
            header += f' "{narration}"'
        if tag_text and getattr(config, 'show_tag', True):
            header += f' {tag_text}'

        lines = [header]
        if getattr(config, 'show_time', True):
            lines.append(f'    time: "{entry_time}"')
        if getattr(config, 'show_uuid', True):
            lines.append(f'    uuid: "{entry_uuid}"')
        if getattr(config, 'show_status', True):
            lines.append(f'    status: "{status}"')
        lines.append(f'    {from_account} -{amount} {currency}')
        lines.append(f'    {to_account} {amount} {currency}')
        return '\n'.join(lines)

    @classmethod
    def _build_entry(
        cls,
        user,
        raw: Dict[str, Any],
        config,
        currency: str,
        tag_paths: Set[str],
    ):
        """校验单条入参并构建暂存区条目；失败返回 (None, 错误信息)。"""
        if not isinstance(raw, dict):
            return None, '条目必须是对象'

        entry_type = str(raw.get('type') or '').strip().lower()
        if entry_type not in ENTRY_TYPES:
            return None, 'type 必须是 expense / income / transfer 之一'

        date = str(raw.get('date') or '').strip()
        if not _DATE_PATTERN.match(date):
            return None, 'date 必须是 YYYY-MM-DD 格式'
        try:
            datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            return None, f'date 不是有效日期: {date}'

        try:
            amount_value = float(raw.get('amount'))
        except (TypeError, ValueError):
            return None, 'amount 必须是数字'
        if amount_value <= 0:
            return None, 'amount 必须大于 0'
        amount = f'{amount_value:.2f}'

        narration = str(raw.get('narration') or '').strip()
        if not narration:
            return None, 'narration 不能为空'
        payee = str(raw.get('payee') or '').strip() or narration

        entry_currency = str(raw.get('currency') or '').strip() or currency
        if entry_currency != currency:
            return None, f'暂不支持非默认币种，当前仅支持 {currency}'

        account = str(raw.get('account') or '').strip()
        payment_account = str(raw.get('payment_account') or '').strip()
        from_account = str(raw.get('from_account') or '').strip()
        to_account = str(raw.get('to_account') or '').strip()

        if entry_type == 'expense':
            if not account.startswith('Expenses:'):
                return None, 'account 必须是 Expenses:* 账户'
            if not (
                payment_account.startswith('Assets:')
                or payment_account.startswith('Liabilities:')
            ):
                return None, 'payment_account 必须是 Assets:* 或 Liabilities:* 账户'
            if not (
                cls._account_exists(user, account)
                and cls._account_exists(user, payment_account)
            ):
                return None, _ACCOUNT_MISSING_MESSAGE
        elif entry_type == 'income':
            if not account.startswith('Income:'):
                return None, 'account 必须是 Income:* 账户'
            if not (
                payment_account.startswith('Assets:')
                or payment_account.startswith('Liabilities:')
            ):
                return None, 'payment_account 必须是 Assets:* 或 Liabilities:* 账户'
            if not (
                cls._account_exists(user, account)
                and cls._account_exists(user, payment_account)
            ):
                return None, _ACCOUNT_MISSING_MESSAGE
        else:
            if not (
                from_account.startswith('Assets:')
                and to_account.startswith('Assets:')
            ):
                return None, 'transfer 的 from_account / to_account 必须是 Assets:* 账户'
            if from_account == to_account:
                return None, 'transfer 的 from_account 与 to_account 不能相同'
            if not (
                cls._account_exists(user, from_account)
                and cls._account_exists(user, to_account)
            ):
                return None, _ACCOUNT_MISSING_MESSAGE

        paths, tag_error = cls._normalize_tags(raw.get('tags'), tag_paths)
        if tag_error:
            return None, tag_error

        entry_uuid = uuid_lib.uuid4().hex
        entry_time = timezone.localtime().strftime('%H:%M:%S')
        status = 'Copilot - 已记录'
        tag_text = ' '.join(f'#{path}' for path in paths) or None
        safe_payee = cls._escape_text(payee)
        safe_narration = cls._escape_text(narration)

        if entry_type == 'transfer':
            formatted = cls._format_transfer(
                date=date,
                config=config,
                payee=safe_payee,
                narration=safe_narration,
                tag_text=tag_text,
                entry_time=entry_time,
                entry_uuid=entry_uuid,
                status=status,
                from_account=from_account,
                to_account=to_account,
                amount=amount,
                currency=entry_currency,
            )
            payment_method = to_account
        else:
            is_expense = entry_type == 'expense'
            formatted = FormatData.format_instance(
                {
                    'date': date,
                    'time': entry_time,
                    'uuid': entry_uuid,
                    'status': status,
                    'payee': safe_payee,
                    'note': safe_narration,
                    'tag': tag_text,
                    'links': [],
                    'currency': entry_currency,
                    'amount': amount,
                    'actual_amount': amount,
                    'discount': None,
                    'expense': account,
                    'expenditure_sign': '' if is_expense else '-',
                    'account': payment_account,
                    'account_sign': '-' if is_expense else '',
                },
                config=config,
            )
            payment_method = payment_account

        formatted_text = (formatted or '').rstrip()
        is_valid, error_message = BeancountValidator.validate_single_entry(formatted_text)
        if not is_valid:
            return None, f'条目 Beancount 语法校验失败: {error_message}'

        transaction_type = _ORIGINAL_ROW_TX_TYPES[entry_type]
        original_row = {
            'transaction_time': f'{date} {entry_time}',
            'transaction_type': transaction_type,
            'counterparty': payee,
            'commodity': narration,
            'amount': amount,
            'payment_method': payment_method,
            'bill_identifier': cls.SOURCE,
            'uuid': entry_uuid,
        }

        entry = {
            'uuid': entry_uuid,
            'formatted': formatted_text,
            'edited_formatted': formatted_text,
            'selected_expense_key': None,
            'expense_candidates_with_score': [],
            'installment_role': None,
            'installment_period': None,
            'tag_details': [
                {'path': path, 'sources': [{'type': 'manual'}]} for path in paths
            ],
            'tag_overrides': ParseReviewService.default_tag_overrides(),
            'original_row': original_row,
            # 供 EntryDedupService 取值
            'date': date,
            'amount': amount,
            'transaction_type': transaction_type,
            'counterparty': payee,
            'commodity': narration,
            'payment_method': payment_method,
        }
        return entry, None

    # ------------------------------------------------------------------
    # 暂存区写入与结果装配
    # ------------------------------------------------------------------
    @classmethod
    def _append_to_staging(cls, user_id, entries: List[Dict[str, Any]]) -> bool:
        """把条目追加到暂存区；已有暂存区不延长审核截止时间。"""
        data = cls.get_staging_data(user_id)
        if data is None:
            now = time.time()
            data = {
                'formatted_data': [],
                'created_at': now,
                'review_expires_at': now + ParseReviewService.REVIEW_DEADLINE_SECONDS,
            }
        data.setdefault('formatted_data', [])
        data['formatted_data'].extend(entries)
        return ParseReviewService.save_parse_result(
            cls.staging_key(user_id),
            data,
            timeout=ParseReviewService.DEFAULT_CACHE_TIMEOUT,
        )

    @classmethod
    def _created_payload(cls, meta: Dict[str, Any]) -> Dict[str, Any]:
        type_label = _TYPE_LABELS.get(meta['type'], meta['type'])
        return {
            'uuid': meta['uuid'],
            'type': meta['type'],
            'date': meta['date'],
            'amount': meta['amount'],
            'currency': meta['currency'],
            'narration': meta['narration'],
            'account': meta['account'],
            'counterparty_account': meta['counterparty_account'],
            'summary': (
                f'{type_label} {meta["date"]} {meta["amount"]} {meta["currency"]} '
                f'{meta["narration"]}'
            ),
        }

    @classmethod
    def _duplicate_payload(cls, meta: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'type': meta['type'],
            'date': meta['date'],
            'amount': meta['amount'],
            'narration': meta['narration'],
            'reason': '与待审核队列中已有条目重复',
        }

    # ------------------------------------------------------------------
    # 主入口
    # ------------------------------------------------------------------
    @classmethod
    def create_entries(cls, user, entries) -> Dict[str, Any]:
        """把 Copilot 给出的交易写入暂存区并加入统一审核队列。

        Returns:
            {'ok': bool, 'created': [...], 'duplicates': [...],
             'errors': [{'index': int|None, 'error': str}], 'pending_total': int}
        """
        result: Dict[str, Any] = {
            'ok': False,
            'created': [],
            'duplicates': [],
            'errors': [],
            'pending_total': cls._staging_count(user.id),
        }

        if not isinstance(entries, list) or not entries:
            result['errors'].append({'index': None, 'error': 'entries 必须是非空数组'})
            return result

        max_entries = cls.max_entries()
        if len(entries) > max_entries:
            result['errors'].append({
                'index': None,
                'error': f'单次最多提交 {max_entries} 笔交易，当前 {len(entries)} 笔',
            })
            return result

        config = get_user_config(user)
        currency = getattr(config, 'currency', None) or 'CNY'
        tag_paths = cls._enabled_tag_paths(user)

        built: List[Dict[str, Any]] = []
        meta_by_uuid: Dict[str, Dict[str, Any]] = {}
        for index, raw in enumerate(entries, start=1):
            entry, error = cls._build_entry(user, raw, config, currency, tag_paths)
            if error:
                result['errors'].append({'index': index, 'error': error})
                continue
            built.append(entry)
            entry_type = str(raw.get('type') or '').strip().lower()
            meta_by_uuid[entry['uuid']] = {
                'uuid': entry['uuid'],
                'type': entry_type,
                'date': entry['date'],
                'amount': entry['amount'],
                'currency': currency,
                'narration': str(raw.get('narration') or '').strip(),
                'account': (
                    raw.get('from_account')
                    if entry_type == 'transfer'
                    else raw.get('account')
                ) or '',
                'counterparty_account': (
                    raw.get('to_account')
                    if entry_type == 'transfer'
                    else raw.get('payment_account')
                ) or '',
            }

        if not built:
            return result

        kept: List[Dict[str, Any]] = []
        duplicates: List[Dict[str, Any]] = []
        acquired = EntryReviewQueueService.acquire_lock(user.id)
        try:
            if acquired:
                existing_entries = EntryReviewQueueService.list_entries(user.id)
                kept, duplicates = EntryDedupService.dedup_new_entries(
                    user, built, existing_entries
                )
            else:
                logger.warning(
                    '未获取到条目审核队列锁，跳过 Copilot 记账去重: user_id=%s',
                    user.id,
                )
                kept, duplicates = list(built), []

            if kept:
                cls._append_to_staging(user.id, kept)
                EntryReviewQueueService.enqueue(
                    user.id, [cls.source_ref(entry['uuid']) for entry in kept]
                )
                EntryReviewQueueService.activate_task(user)
        finally:
            if acquired:
                EntryReviewQueueService.release_lock(user.id)

        result['created'] = [
            cls._created_payload(meta_by_uuid[entry['uuid']]) for entry in kept
        ]
        result['duplicates'] = [
            cls._duplicate_payload(meta_by_uuid[entry['uuid']]) for entry in duplicates
        ]
        result['pending_total'] = len(EntryReviewQueueService.list_entries(user.id))
        result['ok'] = bool(kept)
        return result
