"""get_shouzhi 借贷符号测试。"""
import pytest

from project.apps.translate.services.handlers import get_shouzhi
from project.apps.translate.utils import BILL_ALI, BILL_WECHAT


def _alipay_balance_row(**overrides):
    row = {
        "bill_identifier": BILL_ALI,
        "transaction_type": "/",
        "commodity": "",
        "transaction_status": "交易成功",
        "counterparty": "",
        "payment_method": "",
        "transaction_category": "",
    }
    row.update(overrides)
    return row


class TestGetShouzhi:
    def test_alipay_recharge_normal_returns_high_loss(self):
        data = _alipay_balance_row(commodity="充值-普通充值")
        assert get_shouzhi(data) == ("", "-")

    def test_alipay_yuebao_auto_transfer_returns_high_loss(self):
        data = _alipay_balance_row(commodity="余额宝-自动转入")
        assert get_shouzhi(data) == ("", "-")

    def test_wechat_balance_default_returns_loss_high(self):
        data = {
            "bill_identifier": BILL_WECHAT,
            "transaction_type": "/",
            "commodity": "零钱充值",
            "transaction_status": "支付成功",
            "transaction_category": "充值",
            "counterparty": "",
            "payment_method": "",
        }
        assert get_shouzhi(data) == ("-", "")

    def test_wechat_credit_card_repayment_returns_high_loss(self):
        data = {
            "bill_identifier": BILL_WECHAT,
            "transaction_type": "/",
            "commodity": "",
            "transaction_status": "支付成功",
            "transaction_category": "信用卡还款",
            "counterparty": "",
            "payment_method": "",
        }
        assert get_shouzhi(data) == ("", "-")

    @pytest.mark.parametrize(
        "transaction_type,expected",
        [
            ("支出", ("", "-")),
            ("收入", ("-", "")),
        ],
    )
    def test_expense_and_income_signs(self, transaction_type, expected):
        data = _alipay_balance_row(
            transaction_type=transaction_type,
            commodity="普通消费",
        )
        assert get_shouzhi(data) == expected
