"""为同一笔订单或可判定关联的解析结果分配 Beancount Link（原单号）。

孤立交易不加 link；软匹配不唯一时也不挂，避免误连。
"""
from __future__ import annotations

import re
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional, Set

from project.apps.translate.utils import BILL_ALI, BILL_WECHAT
from project.apps.translate.views.AliPay import alipay_is_refund_row, alipay_parent_uuid

_EMPTY_MERCHANT = frozenset({"", "/", "\\", "-"})

# 微信转账/红包退款类型（用商户单号硬关联，不做商户软匹配）
_WECHAT_HARD_REFUND_CATEGORIES = frozenset({
    "转账-退款",
    "微信红包-退款",
})

# 状态中的退款金额：已退款(¥39.93) / 已退款¥39.93 / 已退款(￥39.93)
_REFUND_AMOUNT_IN_STATUS = re.compile(
    r"已退款\s*[（(]?\s*[¥￥]?\s*([0-9]+(?:\.[0-9]+)?)\s*[)）]?"
)


def _clean_id(value: Optional[str]) -> str:
    if value is None:
        return ""
    return str(value).strip().strip("\t")


def _merchant_order(row: Dict) -> str:
    raw = _clean_id(row.get("merchant_order"))
    if raw in _EMPTY_MERCHANT:
        return ""
    return raw


def _row_uuid(row: Dict) -> str:
    return _clean_id(row.get("uuid"))


def _parse_amount(value) -> Optional[Decimal]:
    if value is None:
        return None
    text = str(value).strip().strip("\t").strip('"')
    text = text.replace("¥", "").replace("￥", "").replace(",", "").replace("\ufeff", "")
    if not text or text in _EMPTY_MERCHANT:
        return None
    try:
        return Decimal(text).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return None


def _amount_from_entry(entry: Dict) -> Optional[Decimal]:
    row = entry.get("_original_row") or {}
    return _parse_amount(row.get("amount")) or _parse_amount(entry.get("amount"))


def _refund_amount_in_status(status: str) -> Optional[Decimal]:
    if not status:
        return None
    match = _REFUND_AMOUNT_IN_STATUS.search(status)
    if not match:
        return None
    return _parse_amount(match.group(1))


def _set_link(entry: Dict, core_id: str) -> None:
    if not core_id:
        return
    links = entry.setdefault("links", [])
    if core_id not in links:
        links.append(core_id)


def _assign_group(entries: List[Dict], core_id: str) -> None:
    if len(entries) < 2 or not core_id:
        return
    for entry in entries:
        _set_link(entry, core_id)


def _assign_alipay_links(entries: List[Dict]) -> Set[int]:
    """支付宝：同 uuid 多行、退款 parent_suffix。返回已硬关联的 entry id。"""
    linked_ids: Set[int] = set()
    by_uuid: Dict[str, List[Dict]] = defaultdict(list)
    by_parent: Dict[str, List[Dict]] = defaultdict(list)

    for entry in entries:
        row = entry.get("_original_row") or {}
        if row.get("bill_identifier") != BILL_ALI:
            continue
        uid = _row_uuid(row) or _clean_id(entry.get("uuid"))
        if not uid:
            continue
        by_uuid[uid].append(entry)

        parent = alipay_parent_uuid(row)
        if parent:
            by_parent[parent].append(entry)
        elif not alipay_is_refund_row(row):
            # 原支付行：uuid 本身即 parent，便于与退款同组
            by_parent[uid].append(entry)

    for uid, group in by_uuid.items():
        if len(group) >= 2:
            _assign_group(group, uid)
            linked_ids.update(id(e) for e in group)

    for parent, group in by_parent.items():
        # 退款单独出现时也挂 ^parent（跨文件已知限制：原单不回写）
        refunds = [e for e in group if alipay_is_refund_row(e.get("_original_row") or {})]
        if not refunds:
            continue
        if len(group) >= 2:
            for entry in group:
                _set_link(entry, parent)
                linked_ids.add(id(entry))
        else:
            # 仅退款一行：仍写 link，便于日后与账本原单成组
            for entry in refunds:
                _set_link(entry, parent)
                linked_ids.add(id(entry))

    return linked_ids


def _is_wechat_transfer_or_redpacket(category: str) -> bool:
    return (
        category.startswith("转账")
        or "微信红包" in category
        or category in _WECHAT_HARD_REFUND_CATEGORIES
    )


def _is_wechat_merchant_refund(category: str) -> bool:
    if not category.endswith("-退款"):
        return False
    return not _is_wechat_transfer_or_redpacket(category)


def _assign_wechat_hard_links(entries: List[Dict]) -> Set[int]:
    """转账/红包：退款.交易单号 == 支付.商户单号，或同商户单号多行。"""
    linked_ids: Set[int] = set()
    wechat_entries = [
        e for e in entries
        if (e.get("_original_row") or {}).get("bill_identifier") == BILL_WECHAT
    ]
    if not wechat_entries:
        return linked_ids

    by_merchant: Dict[str, List[Dict]] = defaultdict(list)
    by_uuid: Dict[str, List[Dict]] = defaultdict(list)

    for entry in wechat_entries:
        row = entry["_original_row"]
        uid = _row_uuid(row)
        merchant = _merchant_order(row)
        if uid:
            by_uuid[uid].append(entry)
        if merchant:
            by_merchant[merchant].append(entry)

    # 退款交易单号 == 某支付商户单号 → 以该商户单号为 core
    for merchant, payers in by_merchant.items():
        refunds = by_uuid.get(merchant, [])
        group = list({id(e): e for e in payers + refunds}.values())
        # 同商户单号多行（发出/自领/退款）或 支付+退款
        if len(group) >= 2 or (payers and refunds):
            members = group if len(group) >= 2 else list(payers) + list(refunds)
            # 去重
            unique = list({id(e): e for e in members}.values())
            if len(unique) >= 2:
                _assign_group(unique, merchant)
                linked_ids.update(id(e) for e in unique)
            elif refunds and payers:
                # 理论上 unique >= 2；兜底
                for entry in unique:
                    _set_link(entry, merchant)
                    linked_ids.add(id(entry))

    # 仅同商户单号 ≥2 且尚未覆盖的（例如发出+自领，退款 uuid 已等于 merchant）
    for merchant, group in by_merchant.items():
        if len(group) >= 2:
            _assign_group(group, merchant)
            linked_ids.update(id(e) for e in group)

    return linked_ids


def _wechat_soft_match_payment(refund_entry: Dict, candidates: List[Dict]) -> Optional[Dict]:
    """商户退款软匹配：同对方 + 状态含退款金额或全额金额相等；不唯一则 None。"""
    refund_row = refund_entry.get("_original_row") or {}
    refund_amount = _amount_from_entry(refund_entry)
    if refund_amount is None:
        return None

    counterparty = (refund_row.get("counterparty") or "").strip()
    if not counterparty:
        return None

    matches: List[Dict] = []
    for payment in candidates:
        pay_row = payment.get("_original_row") or {}
        if (pay_row.get("counterparty") or "").strip() != counterparty:
            continue
        if _is_wechat_merchant_refund(pay_row.get("transaction_category") or ""):
            continue
        # 退款行自身不当作支付候选
        if payment is refund_entry:
            continue

        status = pay_row.get("transaction_status") or ""
        status_amount = _refund_amount_in_status(status)
        pay_amount = _amount_from_entry(payment)

        if status_amount is not None and status_amount == refund_amount:
            matches.append(payment)
            continue
        if status in ("已全额退款", "对方已退还") and pay_amount == refund_amount:
            matches.append(payment)
            continue
        # 部分退：状态写「已退款(¥x)」已在上面覆盖；也可匹配支出行金额相等且状态含「已退款」
        if "已退款" in status and pay_amount == refund_amount and status_amount is None:
            matches.append(payment)

    if len(matches) == 1:
        return matches[0]
    return None


def _assign_wechat_soft_links(entries: List[Dict], already_linked: Set[int]) -> None:
    wechat_entries = [
        e for e in entries
        if (e.get("_original_row") or {}).get("bill_identifier") == BILL_WECHAT
    ]
    payments = [
        e for e in wechat_entries
        if not _is_wechat_merchant_refund(
            (e.get("_original_row") or {}).get("transaction_category") or ""
        )
        and not (
            ((e.get("_original_row") or {}).get("transaction_category") or "")
            in _WECHAT_HARD_REFUND_CATEGORIES
        )
    ]
    refunds = [
        e for e in wechat_entries
        if _is_wechat_merchant_refund(
            (e.get("_original_row") or {}).get("transaction_category") or ""
        )
        and id(e) not in already_linked
    ]

    # 按支付 uuid 聚合多笔退款（一付多退）
    payment_to_refunds: Dict[int, List[Dict]] = defaultdict(list)
    payment_core: Dict[int, str] = {}

    for refund in refunds:
        match = _wechat_soft_match_payment(refund, payments)
        if not match:
            continue
        pay_row = match.get("_original_row") or {}
        core = _row_uuid(pay_row)
        if not core:
            continue
        pid = id(match)
        payment_to_refunds[pid].append(refund)
        payment_core[pid] = core

    for pid, refund_list in payment_to_refunds.items():
        payment = next(e for e in payments if id(e) == pid)
        core = payment_core[pid]
        _set_link(payment, core)
        for refund in refund_list:
            _set_link(refund, core)


def assign_transaction_links(parsed_entries: List[Dict]) -> None:
    """二次扫描：为可关联条目写入 entry['links'] = [core_id]。原地修改。"""
    if not parsed_entries:
        return

    for entry in parsed_entries:
        entry.setdefault("links", [])

    alipay_linked = _assign_alipay_links(parsed_entries)
    wechat_hard = _assign_wechat_hard_links(parsed_entries)
    _assign_wechat_soft_links(parsed_entries, alipay_linked | wechat_hard)
