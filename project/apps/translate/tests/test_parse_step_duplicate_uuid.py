"""同一交易订单号出现多行时，应独立解析且审核身份不碰撞。"""
from unittest.mock import MagicMock, patch

from project.apps.translate.services.steps import ParseStep, allocate_unique_cache_key
from project.apps.translate.utils import BILL_ALI


def _alipay_row(**overrides):
    row = {
        "transaction_time": "2026-04-01 10:00:00",
        "transaction_category": "日用百货",
        "counterparty": "测试商家",
        "commodity": "组合支付",
        "transaction_type": "支出",
        "amount": 10.0,
        "payment_method": "花呗",
        "transaction_status": "交易成功",
        "notes": "/",
        "bill_identifier": BILL_ALI,
        "uuid": "ORDER123",
        "discount": False,
    }
    row.update(overrides)
    return row


def _parsed_from_row(row, *_args, **_kwargs):
    return {
        "uuid": row["uuid"],
        "amount": f"{float(row['amount']):.2f}",
        "expense": f"Expenses:{row['payment_method']}",
        "account": "Assets:Digital:Alipay",
        "note": row["commodity"],
    }


class TestAllocateUniqueCacheKey:
    def test_first_keeps_base(self):
        seen = {}
        assert allocate_unique_cache_key("ORDER123", seen) == "ORDER123"

    def test_duplicates_get_suffix(self):
        seen = {}
        assert allocate_unique_cache_key("ORDER123", seen) == "ORDER123"
        assert allocate_unique_cache_key("ORDER123", seen) == "ORDER123--2"
        assert allocate_unique_cache_key("ORDER123", seen) == "ORDER123--3"

    def test_distinct_bases_unaffected(self):
        seen = {}
        assert allocate_unique_cache_key("A", seen) == "A"
        assert allocate_unique_cache_key("B", seen) == "B"


class TestParseStepDuplicateOrderUuid:
    def _execute(self, rows):
        context = {
            "owner_id": 1,
            "user": MagicMock(),
            "config": MagicMock(),
            "prefilter_bill": rows,
        }
        return ParseStep().execute(context)

    @patch("project.apps.translate.services.steps.build_ledger_index_for_user", return_value={})
    @patch(
        "project.apps.translate.services.steps.single_parse_transaction",
        side_effect=_parsed_from_row,
    )
    def test_same_order_number_parses_independently(self, _mock_parse, _mock_ledger):
        result = self._execute(
            [
                _alipay_row(amount=80.0, payment_method="花呗"),
                _alipay_row(amount=20.0, payment_method="余额"),
            ]
        )
        parsed = result["parsed_data"]

        assert len(parsed) == 2
        assert parsed[0]["amount"] == "80.00"
        assert parsed[1]["amount"] == "20.00"
        assert parsed[0]["expense"] == "Expenses:花呗"
        assert parsed[1]["expense"] == "Expenses:余额"
        assert parsed[0]["uuid"] == parsed[1]["uuid"] == "ORDER123"
        assert parsed[0]["cache_key"] == "ORDER123"
        assert parsed[1]["cache_key"] == "ORDER123--2"
        assert parsed[0]["_original_row"]["payment_method"] == "花呗"
        assert parsed[1]["_original_row"]["payment_method"] == "余额"

    @patch("project.apps.translate.services.steps.build_ledger_index_for_user", return_value={})
    @patch(
        "project.apps.translate.services.steps.single_parse_transaction",
        side_effect=_parsed_from_row,
    )
    def test_unique_order_number_keeps_uuid_as_cache_key(self, mock_parse, _mock_ledger):
        result = self._execute(
            [
                _alipay_row(uuid="OID-A", amount=10.0),
                _alipay_row(uuid="OID-B", amount=20.0),
            ]
        )
        parsed = result["parsed_data"]

        assert parsed[0]["cache_key"] == "OID-A"
        assert parsed[1]["cache_key"] == "OID-B"
        assert mock_parse.call_count == 2
