# project/apps/translate/services/alipay_refund_peer.py
"""支付宝退款与原单科目关联（同账单 + 账本）。"""
from __future__ import annotations

from typing import Callable, Dict, List, Optional

from project.apps.translate.services.ledger_uuid_index import (
    LedgerUuidIndexService,
    RefundPeerSnapshot,
    snapshot_from_parsed_entry,
)
from project.apps.translate.utils import BILL_ALI
from project.apps.translate.views.AliPay import (
    alipay_is_payment_row,
    alipay_is_refund_row,
    alipay_parent_uuid,
)


def build_raw_payment_index(bill_rows: List[Dict]) -> Dict[str, Dict]:
    """预扫描：uuid -> 原支付行（与账单行顺序无关）。"""
    index: Dict[str, Dict] = {}
    for row in bill_rows:
        if row.get("bill_identifier") != BILL_ALI:
            continue
        if not alipay_is_payment_row(row):
            continue
        uid = (row.get("uuid") or "").strip()
        if uid:
            index[uid] = row
    return index


def resolve_alipay_refund_peer(
    parent_uuid: Optional[str],
    parse_cache: Dict[str, Dict],
    raw_payment_index: Dict[str, Dict],
    ledger_index: Dict[str, RefundPeerSnapshot],
    lazy_parse_fn: Callable[[Dict], Dict],
) -> Optional[RefundPeerSnapshot]:
    """L1 parse_cache -> L1 惰性解析 -> L2 ledger。"""
    if not parent_uuid:
        return None

    cached = parse_cache.get(parent_uuid)
    if cached:
        return snapshot_from_parsed_entry(cached)

    raw_row = raw_payment_index.get(parent_uuid)
    if raw_row:
        parsed = lazy_parse_fn(raw_row)
        parse_cache[parent_uuid] = parsed
        return snapshot_from_parsed_entry(parsed)

    return ledger_index.get(parent_uuid)


def build_ledger_index_for_user(user) -> Dict[str, RefundPeerSnapshot]:
    return LedgerUuidIndexService.build_for_user(user)


def resolve_refund_peer_for_row(
    row: Dict,
    user,
    owner_id: int,
    config,
    selected_key: Optional[str] = None,
) -> Optional[RefundPeerSnapshot]:
    """单条重解析时解析退款 peer（仅 L2 账本 + 无同批账单）。"""
    if not alipay_is_refund_row(row):
        return None
    from project.apps.translate.services.parse.transaction_parser import (
        single_parse_transaction,
    )

    ledger_index = build_ledger_index_for_user(user) if user else {}
    return resolve_alipay_refund_peer(
        alipay_parent_uuid(row),
        {},
        {},
        ledger_index,
        lambda payment_row: single_parse_transaction(
            payment_row, owner_id, config, None
        ),
    )
