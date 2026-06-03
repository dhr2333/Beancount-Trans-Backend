# project/apps/translate/services/ledger_uuid_index.py
"""从用户 bean 账本按 uuid 索引原交易科目，供退款关联使用。"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from beancount import loader
from beancount.core.data import Transaction

from project.utils.file import BeanFileManager

logger = logging.getLogger(__name__)

# 费用侧账户前缀（按优先级）
_EXPENSE_SIDE_PREFIXES = ("Expenses:", "Income:", "Equity:")


@dataclass
class RefundPeerSnapshot:
    expense_account: str
    selected_expense_key: Optional[str] = None


def _posting_amount_magnitude(posting) -> Decimal:
    if posting.units is None:
        return Decimal(0)
    return abs(posting.units.number)


def extract_expense_account_from_postings(postings) -> Optional[str]:
    """从 Transaction postings 中取费用侧账户（绝对金额最大的一条）。"""
    candidates: List[Tuple[Decimal, int, str]] = []
    for posting in postings or []:
        account = posting.account
        if account.startswith("Assets:") or account.startswith("Liabilities:"):
            continue
        for pri, prefix in enumerate(_EXPENSE_SIDE_PREFIXES):
            if account.startswith(prefix):
                candidates.append((_posting_amount_magnitude(posting), pri, account))
                break
    if not candidates:
        return None
    candidates.sort(key=lambda x: (-x[0], x[1]))
    return candidates[0][2]


class LedgerUuidIndexService:
    @staticmethod
    def build_for_user(user) -> Dict[str, RefundPeerSnapshot]:
        """加载 main.bean，构建 uuid -> 原单费用科目索引。"""
        main_bean_path = BeanFileManager.get_main_bean_path(user)
        if not os.path.exists(main_bean_path):
            return {}

        try:
            entries, errors, _options = loader.load_file(main_bean_path)
        except Exception as e:
            logger.error("加载账本失败 %s: %s", main_bean_path, e)
            return {}

        if errors:
            logger.warning("账本加载有 %s 个警告/错误", len(errors))

        index: Dict[str, RefundPeerSnapshot] = {}
        for entry in entries:
            if not isinstance(entry, Transaction):
                continue
            meta = getattr(entry, "meta", None) or {}
            entry_uuid = meta.get("uuid")
            if not entry_uuid:
                continue
            expense_account = extract_expense_account_from_postings(entry.postings)
            if not expense_account:
                continue
            index[str(entry_uuid)] = RefundPeerSnapshot(expense_account=expense_account)

        return index


def snapshot_from_parsed_entry(parsed: Dict) -> RefundPeerSnapshot:
    """从本批已解析条目提取 peer 快照。"""
    return RefundPeerSnapshot(
        expense_account=parsed["expense"],
        selected_expense_key=parsed.get("selected_expense_key"),
    )
