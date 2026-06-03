"""Payee 跟随 selected_expense_key 测试。"""
from types import SimpleNamespace

import pytest

from project.apps.account.models import Account
from project.apps.maps.models import Expense, Income
from project.apps.translate.services.handlers import PayeeHandler
from project.apps.translate.services.parse.transaction_parser import single_parse_transaction
from project.apps.translate.utils import BILL_ALI, BILL_WECHAT


@pytest.fixture
def expense_accounts(user):
    shallow = Account.objects.create(account="Expenses:Shopping", owner=user)
    deep = Account.objects.create(account="Expenses:Shopping:Parent", owner=user)
    return shallow, deep


@pytest.fixture
def payee_mapping_user(user, expense_accounts):
    shallow, deep = expense_accounts
    Expense.objects.create(
        key="十月结晶",
        payee="十月结晶",
        expend=shallow,
        owner=user,
        enable=True,
    )
    Expense.objects.create(
        key="出行",
        payee="出行商户",
        expend=deep,
        owner=user,
        enable=True,
    )
    return user


def _expense_row(**overrides):
    row = {
        "transaction_time": "2024-02-25 20:01:48",
        "transaction_category": "母婴亲子",
        "counterparty": "十月**店",
        "commodity": "十月结晶会员出行必备",
        "transaction_type": "支出",
        "amount": 14.8,
        "payment_method": "支付宝",
        "transaction_status": "交易成功",
        "notes": "/",
        "bill_identifier": BILL_ALI,
        "uuid": "test-payee-uuid-1",
        "discount": False,
    }
    row.update(overrides)
    return row


@pytest.mark.django_db
class TestPayeeFollowsSelectedKey:
    def test_selected_key_payee_overrides_general_priority(self, payee_mapping_user):
        row = _expense_row()
        handler = PayeeHandler(row)
        owner_id = payee_mapping_user.id
        assert (
            handler.get_payee(row, owner_id, selected_mapping_key="十月结晶")
            == "十月结晶"
        )
        assert handler.get_payee(row, owner_id, selected_mapping_key=None) == "出行商户"

    def test_empty_mapping_payee_falls_back_to_counterparty(self, user, expense_accounts):
        shallow, _ = expense_accounts
        Expense.objects.create(
            key="nostore",
            payee="",
            expend=shallow,
            owner=user,
            enable=True,
        )
        row = _expense_row(counterparty="原始商户", commodity="nostore购物")
        handler = PayeeHandler(row)
        assert (
            handler.get_payee(row, user.id, selected_mapping_key="nostore")
            == "原始商户"
        )

    def test_income_uses_payer(self, user):
        income_acc = Account.objects.create(account="Income:Salary", owner=user)
        Income.objects.create(
            key="工资",
            payer="雇主",
            income=income_acc,
            owner=user,
            enable=True,
        )
        row = _expense_row(
            transaction_type="收入",
            counterparty="某公司",
            commodity="工资到账",
        )
        handler = PayeeHandler(row)
        assert handler.get_payee(row, user.id, selected_mapping_key="工资") == "雇主"

    def test_special_case_takes_precedence(self, payee_mapping_user):
        row = _expense_row(
            bill_identifier=BILL_WECHAT,
            transaction_category="微信红包-退款",
        )
        handler = PayeeHandler(row)
        assert (
            handler.get_payee(
                row, payee_mapping_user.id, selected_mapping_key="十月结晶"
            )
            == "退款"
        )

    def test_single_parse_with_selected_key(self, payee_mapping_user):
        row = _expense_row()
        config = SimpleNamespace(ai_model="None", deepseek_apikey=None, flag="*")
        parsed = single_parse_transaction(
            row, payee_mapping_user.id, config, "十月结晶"
        )
        assert parsed["selected_expense_key"] == "十月结晶"
        assert parsed["payee"] == "十月结晶"
