"""支付宝退款关联原单账户测试。"""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from beancount.core.amount import Amount
from beancount.core.data import Posting
from beancount.core.number import D

from project.apps.translate.services.alipay_refund_peer import (
    build_raw_payment_index,
    resolve_alipay_refund_peer,
)
from project.apps.translate.services.ledger_uuid_index import (
    RefundPeerSnapshot,
    extract_expense_account_from_postings,
)
from project.apps.translate.services.parse.transaction_parser import single_parse_transaction
from project.apps.translate.utils import BILL_ALI, EXPENSES_OTHER
from project.apps.translate.views.AliPay import (
    alipay_is_payment_row,
    alipay_is_refund_row,
    alipay_parent_uuid,
)

PARENT_UUID = "2026050122001474561404868314"
REFUND_UUID = f"{PARENT_UUID}_331266000048210001260501111599286666"


def _parse_config():
    return SimpleNamespace(ai_model="None", deepseek_apikey=None, flag="*")


def _payment_row(**overrides):
    row = {
        "transaction_time": "2026-04-01 10:00:00",
        "transaction_category": "交通出行",
        "counterparty": "浙江新闪新能源科技有限公司",
        "commodity": "充电消费",
        "transaction_type": "/",
        "amount": 85.81,
        "payment_method": "中国银行储蓄卡(0814)",
        "transaction_status": "交易成功",
        "notes": "/",
        "bill_identifier": BILL_ALI,
        "uuid": PARENT_UUID,
        "discount": False,
    }
    row.update(overrides)
    return row


def _refund_row(**overrides):
    row = _payment_row(
        transaction_time="2026-05-01 12:41:37",
        commodity="退款-商品信息",
        transaction_status="退款成功",
        uuid=REFUND_UUID,
        **overrides,
    )
    return row


@pytest.mark.django_db
class TestAlipayRefundHelpers:
    def test_parent_uuid_splits_suffix(self):
        assert alipay_parent_uuid(_refund_row()) == PARENT_UUID

    def test_parent_uuid_without_suffix(self):
        assert alipay_parent_uuid(_payment_row()) is None

    def test_is_refund_and_payment_row(self):
        assert alipay_is_refund_row(_refund_row())
        assert alipay_is_payment_row(_payment_row())
        assert not alipay_is_payment_row(_refund_row())


class TestExtractExpenseFromPostings:
    def test_picks_largest_non_asset_posting(self):
        postings = [
            Posting("Assets:Bank", Amount(D("-85.81"), "CNY"), None, None, None, None),
            Posting("Expenses:Transport:EV", Amount(D("85.81"), "CNY"), None, None, None, None),
        ]
        assert extract_expense_account_from_postings(postings) == "Expenses:Transport:EV"


class TestResolveAlipayRefundPeer:
    def test_resolve_from_parse_cache(self):
        parse_cache = {
            PARENT_UUID: {
                "expense": "Expenses:Transport:EV",
                "selected_expense_key": "充电",
            }
        }
        peer = resolve_alipay_refund_peer(
            PARENT_UUID, parse_cache, {}, {}, lambda r: {}
        )
        assert peer.expense_account == "Expenses:Transport:EV"
        assert peer.selected_expense_key == "充电"

    def test_resolve_from_raw_index_lazy_parse(self):
        payment = _payment_row()
        parsed_holder = []

        def lazy_parse(row):
            parsed = {
                "expense": "Expenses:Food:Lunch",
                "selected_expense_key": "午餐",
            }
            parsed_holder.append(row)
            return parsed

        peer = resolve_alipay_refund_peer(
            PARENT_UUID,
            {},
            {PARENT_UUID: payment},
            {},
            lazy_parse,
        )
        assert peer.expense_account == "Expenses:Food:Lunch"
        assert parsed_holder[0] is payment

    def test_resolve_from_ledger_index(self):
        ledger = {
            PARENT_UUID: RefundPeerSnapshot("Expenses:Shopping:Online"),
        }
        peer = resolve_alipay_refund_peer(
            PARENT_UUID, {}, {}, ledger, lambda r: {}
        )
        assert peer.expense_account == "Expenses:Shopping:Online"

    def test_reverse_order_raw_index_before_cache(self):
        """退款行在原单之前时，仍可通过 raw_payment_index 关联。"""
        payment = _payment_row()
        raw_index = build_raw_payment_index([_refund_row(), payment])
        assert PARENT_UUID in raw_index

        peer = resolve_alipay_refund_peer(
            PARENT_UUID,
            {},
            raw_index,
            {},
            lambda r: {
                "expense": "Expenses:Transport:EV",
                "selected_expense_key": None,
            },
        )
        assert peer.expense_account == "Expenses:Transport:EV"


@pytest.mark.django_db
class TestSingleParseWithRefundPeer:
    @patch("project.apps.translate.services.handlers.get_default_assets")
    @patch("project.apps.translate.services.handlers.get_mapping_provider")
    def test_refund_uses_peer_expense(self, mock_provider, mock_assets, user):
        mock_assets.return_value = {
            "ALIPAY": "Assets:Digital:Alipay",
            "WECHATPAY": "Assets:Digital:WeChat",
            "WECHATFUND": "Assets:Digital:WeChatFund",
            "ALIFUND": "Assets:Digital:Alifund",
            "HUABEI": "Liabilities:Huabei",
            "JIEBEI": "Liabilities:Jiebei",
            "BEIYONGJIN": "Liabilities:Beiyongjin",
        }
        provider = MagicMock()
        provider.get_expense_mappings.return_value = []
        provider.get_income_mappings.return_value = []
        provider.get_asset_mappings.return_value = []
        mock_provider.return_value = provider

        peer = RefundPeerSnapshot("Expenses:Transport:EV", "充电")

        parsed = single_parse_transaction(
            _refund_row(), user.id, _parse_config(), None, refund_peer=peer
        )
        assert parsed["expense"] == "Expenses:Transport:EV"
        assert parsed["expense"] != "Assets:Other"

    @patch("project.apps.translate.services.handlers.get_default_assets")
    @patch("project.apps.translate.services.handlers.get_mapping_provider")
    def test_refund_fallback_not_assets_other(self, mock_provider, mock_assets, user):
        mock_assets.return_value = {
            "ALIPAY": "Assets:Digital:Alipay",
            "WECHATPAY": "Assets:Digital:WeChat",
            "WECHATFUND": "Assets:Digital:WeChatFund",
            "ALIFUND": "Assets:Digital:Alifund",
            "HUABEI": "Liabilities:Huabei",
            "JIEBEI": "Liabilities:Jiebei",
            "BEIYONGJIN": "Liabilities:Beiyongjin",
        }
        provider = MagicMock()
        provider.get_expense_mappings.return_value = []
        provider.get_income_mappings.return_value = []
        provider.get_asset_mappings.return_value = []
        mock_provider.return_value = provider

        parsed = single_parse_transaction(_refund_row(), user.id, _parse_config(), None)
        assert parsed["expense"] == EXPENSES_OTHER
        assert parsed["expense"] != "Assets:Other"
