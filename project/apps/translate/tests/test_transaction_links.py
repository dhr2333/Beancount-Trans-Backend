"""Beancount Link（^原单号）自动关联测试。"""
from project.apps.translate.services.parse.link_resolver import assign_transaction_links
from project.apps.translate.utils import BILL_ALI, BILL_WECHAT, FormatConfig, FormatData


def _entry(row, **overrides):
    entry = {
        "date": "2026-07-27",
        "time": "21:08:58",
        "uuid": row.get("uuid"),
        "status": f"WeChat - {row.get('transaction_status', '')}",
        "payee": row.get("counterparty"),
        "note": row.get("commodity"),
        "tag": None,
        "links": [],
        "expense": "Expenses:Other",
        "expenditure_sign": "",
        "account": "Assets:Digital:WeChat",
        "account_sign": "-",
        "amount": f"{float(row.get('amount', 0)):.2f}",
        "discount": False,
        "currency": "CNY",
        "_original_row": row,
    }
    entry.update(overrides)
    return entry


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


def _wechat_row(**overrides):
    row = {
        "transaction_time": "2026-07-27 21:08:58",
        "transaction_category": "商户消费",
        "counterparty": "飞宇智能",
        "commodity": "商品",
        "transaction_type": "支出",
        "amount": 1.01,
        "payment_method": "零钱",
        "transaction_status": "已退款(¥1.01)",
        "notes": "/",
        "bill_identifier": BILL_WECHAT,
        "uuid": "4500000248202607274339337014",
        "merchant_order": "20260727210858742",
        "discount": False,
    }
    row.update(overrides)
    return row


class TestAlipayLinks:
    def test_same_order_uuid_shares_link(self):
        entries = [
            _entry(_alipay_row(amount=80.0, payment_method="花呗")),
            _entry(_alipay_row(amount=20.0, payment_method="余额")),
        ]
        assign_transaction_links(entries)
        assert entries[0]["links"] == ["ORDER123"]
        assert entries[1]["links"] == ["ORDER123"]

    def test_refund_and_payment_share_parent_link(self):
        parent = "2025061422001174561430097109"
        payment = _entry(_alipay_row(uuid=parent, amount=1772.06))
        refund = _entry(
            _alipay_row(
                uuid=f"{parent}_3028196317180476065",
                transaction_status="退款成功",
                amount=100.0,
                commodity="退款-商品",
            )
        )
        assign_transaction_links([payment, refund])
        assert payment["links"] == [parent]
        assert refund["links"] == [parent]

    def test_refund_alone_still_gets_parent_link(self):
        parent = "2025061422001174561430097109"
        refund = _entry(
            _alipay_row(
                uuid=f"{parent}_suffix",
                transaction_status="退款成功",
                amount=50.0,
            )
        )
        assign_transaction_links([refund])
        assert refund["links"] == [parent]

    def test_isolated_payment_has_no_link(self):
        entry = _entry(_alipay_row(uuid="ONLY-ONE"))
        assign_transaction_links([entry])
        assert entry["links"] == []


class TestWeChatHardLinks:
    def test_transfer_refund_links_by_merchant_order(self):
        merchant = "1000050001202304140613257249726"
        payment = _entry(
            _wechat_row(
                transaction_category="转账",
                counterparty="张三",
                uuid="1000050001202304140613257249999",
                merchant_order=merchant,
                amount=3.0,
                transaction_status="已全额退款",
            )
        )
        refund = _entry(
            _wechat_row(
                transaction_category="转账-退款",
                counterparty="张三",
                transaction_type="收入",
                uuid=merchant,
                merchant_order="/",
                amount=3.0,
                transaction_status="已全额退款",
            )
        )
        assign_transaction_links([payment, refund])
        assert payment["links"] == [merchant]
        assert refund["links"] == [merchant]

    def test_same_merchant_order_group_redpacket(self):
        merchant = "1000039901202404116201987557015"
        send = _entry(
            _wechat_row(
                transaction_category="微信红包（群红包）",
                uuid="TX-SEND",
                merchant_order=merchant,
                amount=100.0,
                transaction_status="支付成功",
            )
        )
        claim = _entry(
            _wechat_row(
                transaction_category="微信红包（群红包）",
                transaction_type="收入",
                uuid="TX-CLAIM",
                merchant_order=merchant,
                amount=40.0,
                transaction_status="已存入零钱",
            )
        )
        assign_transaction_links([send, claim])
        assert send["links"] == [merchant]
        assert claim["links"] == [merchant]


class TestWeChatSoftLinks:
    def test_merchant_partial_refund_soft_match(self):
        """飞宇形态：单号无交叉，靠对方 + 状态金额软关联。"""
        pay_uuid = "4500000248202607274339337014"
        payment = _entry(
            _wechat_row(
                uuid=pay_uuid,
                merchant_order="20260727210858742",
                amount=1.01,
                transaction_status="已退款(¥1.01)",
                counterparty="飞宇智能",
                transaction_category="商户消费",
            )
        )
        refund = _entry(
            _wechat_row(
                uuid="50301408052026072843875043118",
                merchant_order="/",
                amount=1.01,
                transaction_type="收入",
                transaction_status="已退款¥1.01",
                counterparty="飞宇智能",
                transaction_category="飞宇智能-退款",
            )
        )
        assign_transaction_links([payment, refund])
        assert payment["links"] == [pay_uuid]
        assert refund["links"] == [pay_uuid]

    def test_ambiguous_soft_match_skips_link(self):
        pay_a = _entry(
            _wechat_row(
                uuid="PAY-A",
                merchant_order="M-A",
                amount=10.0,
                transaction_status="已退款(¥5.00)",
                counterparty="同店",
            )
        )
        pay_b = _entry(
            _wechat_row(
                uuid="PAY-B",
                merchant_order="M-B",
                amount=20.0,
                transaction_status="已退款(¥5.00)",
                counterparty="同店",
            )
        )
        refund = _entry(
            _wechat_row(
                uuid="REF-X",
                merchant_order="/",
                amount=5.0,
                transaction_type="收入",
                transaction_status="已退款¥5.00",
                counterparty="同店",
                transaction_category="同店-退款",
            )
        )
        assign_transaction_links([pay_a, pay_b, refund])
        assert pay_a["links"] == []
        assert pay_b["links"] == []
        assert refund["links"] == []

    def test_isolated_wechat_has_no_link(self):
        entry = _entry(_wechat_row(transaction_status="支付成功"))
        assign_transaction_links([entry])
        assert entry["links"] == []


class TestFormatInstanceLinks:
    def test_link_appears_after_tag_before_metadata(self):
        entry = {
            "date": "2025-06-14",
            "payee": "壹号**私",
            "note": "床 等多件6期",
            "tag": "#Project/Decoration",
            "links": ["2025061422001174561430097109"],
            "time": "09:40:16",
            "uuid": "2025061422001174561430097109",
            "status": "ALiPay - 交易成功",
            "expense": "Expenses:Home:Decoration",
            "expenditure_sign": "",
            "account": "Liabilities:Payables",
            "account_sign": "-",
            "amount": "1772.06",
            "discount": False,
            "currency": "CNY",
        }
        text = FormatData.format_instance(entry, FormatConfig())
        first_line = text.split("\n", 1)[0]
        assert first_line.endswith("^2025061422001174561430097109")
        assert "#Project/Decoration ^2025061422001174561430097109" in first_line
        assert 'uuid: "2025061422001174561430097109"' in text

    def test_no_links_omits_caret(self):
        entry = {
            "date": "2025-06-14",
            "payee": "店",
            "note": "商品",
            "tag": None,
            "links": [],
            "time": "09:40:16",
            "uuid": "ONLY",
            "status": "WeChat - 支付成功",
            "expense": "Expenses:Other",
            "expenditure_sign": "",
            "account": "Assets:Digital:WeChat",
            "account_sign": "-",
            "amount": "1.00",
            "discount": False,
            "currency": "CNY",
        }
        text = FormatData.format_instance(entry, FormatConfig())
        assert "^" not in text.split("\n", 1)[0]
