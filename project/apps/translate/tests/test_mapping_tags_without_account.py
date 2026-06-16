"""无映射账户时仍应用标签测试。"""
from types import SimpleNamespace

import pytest
from unittest.mock import patch

from project.apps.account.models import Account
from project.apps.maps.models import Expense, Income
from project.apps.tags.models import Tag
from project.apps.translate.services.handlers import PayeeHandler
from project.apps.translate.services.parse.transaction_parser import single_parse_transaction
from project.apps.translate.utils import BILL_ALI, EXPENSES_OTHER, INCOME_OTHER


def _parse_config(**overrides):
    defaults = {
        "ai_model": "None",
        "deepseek_apikey": None,
        "flag": "*",
        "reconciliation_fallback_account": None,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _default_assets():
    return {
        "ALIPAY": "Assets:Digital:Alipay",
        "WECHATPAY": "Assets:Digital:WeChat",
        "WECHATFUND": "Assets:Digital:WeChatFund",
        "ALIFUND": "Assets:Digital:Alifund",
        "HUABEI": "Liabilities:Huabei",
        "JIEBEI": "Liabilities:Jiebei",
        "BEIYONGJIN": "Liabilities:Beiyongjin",
    }


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
        "uuid": "test-tag-no-account-1",
        "discount": False,
    }
    row.update(overrides)
    return row


def _income_row(**overrides):
    defaults = {
        "transaction_type": "收入",
        "transaction_category": "转账红包",
        "counterparty": "某公司",
        "commodity": "工资到账",
    }
    defaults.update(overrides)
    return _expense_row(**defaults)


@pytest.mark.django_db
class TestExpenseMappingTagsWithoutAccount:
    @patch("project.apps.translate.services.handlers.get_default_assets")
    def test_tag_applied_with_fallback_expense_account(self, mock_assets, user):
        mock_assets.return_value = _default_assets()
        tag = Tag.objects.create(name="Irregular", owner=user)
        mapping = Expense.objects.create(
            key="十月结晶",
            expend=None,
            owner=user,
            enable=True,
        )
        mapping.tags.add(tag)

        parsed = single_parse_transaction(
            _expense_row(),
            user.id,
            _parse_config(),
            None,
        )

        assert parsed["expense"] == EXPENSES_OTHER
        assert parsed["selected_expense_key"] == "十月结晶"
        assert parsed["tag"] == "#Irregular"
        assert parsed["expense_candidates_with_score"] == [{"key": "十月结晶", "score": 0.0}]

    @patch("project.apps.translate.services.handlers.get_default_assets")
    def test_mixed_candidates_no_account_mapping_has_zero_similarity(self, mock_assets, user):
        mock_assets.return_value = _default_assets()
        tag_only = Tag.objects.create(name="TagOnly", owner=user)
        account = Account.objects.create(account="Expenses:Shopping", owner=user)

        tag_only_mapping = Expense.objects.create(
            key="十月结晶",
            expend=None,
            owner=user,
            enable=True,
        )
        tag_only_mapping.tags.add(tag_only)
        Expense.objects.create(
            key="十月",
            expend=account,
            owner=user,
            enable=True,
        )

        parsed = single_parse_transaction(
            _expense_row(commodity="十月结晶会员十月购物"),
            user.id,
            _parse_config(),
            None,
        )

        scores = {item["key"]: item["score"] for item in parsed["expense_candidates_with_score"]}
        assert scores["十月结晶"] == 0.0
        assert scores["十月"] == 1.0

    @patch("project.apps.translate.services.handlers.get_default_assets")
    @patch("project.apps.translate.services.handlers.BertSimilarity")
    def test_ai_conflict_excludes_no_account_from_similarity(self, mock_bert_cls, mock_assets, user):
        mock_assets.return_value = _default_assets()
        account = Account.objects.create(account="Expenses:Shopping", owner=user)
        Expense.objects.create(key="十月结晶", expend=None, owner=user, enable=True)
        Expense.objects.create(key="十月", expend=account, owner=user, enable=True)

        mock_bert_cls.return_value.calculate_similarity.return_value = {
            "best_match": "十月",
            "scores": {"十月": 0.88, "十月结晶": 0.99},
        }

        parsed = single_parse_transaction(
            _expense_row(commodity="十月结晶会员十月购物"),
            user.id,
            _parse_config(ai_model="BERT"),
            None,
        )

        scores = {item["key"]: item["score"] for item in parsed["expense_candidates_with_score"]}
        assert parsed["selected_expense_key"] == "十月"
        assert scores["十月结晶"] == 0.0
        assert scores["十月"] == 0.88

    @patch("project.apps.translate.services.handlers.get_default_assets")
    def test_mixed_candidates_use_account_mapping_and_merge_tags(self, mock_assets, user):
        mock_assets.return_value = _default_assets()
        tag_only = Tag.objects.create(name="TagOnly", owner=user)
        tag_with_account = Tag.objects.create(name="TagWithAccount", owner=user)
        account = Account.objects.create(account="Expenses:Shopping", owner=user)

        tag_only_mapping = Expense.objects.create(
            key="十月结晶",
            expend=None,
            owner=user,
            enable=True,
        )
        tag_only_mapping.tags.add(tag_only)

        account_mapping = Expense.objects.create(
            key="十月",
            expend=account,
            owner=user,
            enable=True,
        )
        account_mapping.tags.add(tag_with_account)

        parsed = single_parse_transaction(
            _expense_row(commodity="十月结晶会员十月购物"),
            user.id,
            _parse_config(),
            None,
        )

        assert parsed["expense"] == "Expenses:Shopping"
        assert parsed["selected_expense_key"] == "十月"
        assert "#TagOnly" in parsed["tag"]
        assert "#TagWithAccount" in parsed["tag"]
        tag_only_detail = next(item for item in parsed["tag_details"] if item["path"] == "TagOnly")
        tag_with_account_detail = next(
            item for item in parsed["tag_details"] if item["path"] == "TagWithAccount"
        )
        assert tag_only_detail["sources"] == [{
            "type": "mapping",
            "key": "十月结晶",
            "mapping_type": "expense",
        }]
        assert tag_with_account_detail["sources"] == [{
            "type": "mapping",
            "key": "十月",
            "mapping_type": "expense",
        }]

    @patch("project.apps.translate.services.handlers.get_default_assets")
    def test_manual_selected_key_without_account_still_applies_tags(self, mock_assets, user):
        mock_assets.return_value = _default_assets()
        tag = Tag.objects.create(name="ManualTag", owner=user)
        account = Account.objects.create(account="Expenses:Shopping", owner=user)

        tag_mapping = Expense.objects.create(
            key="十月结晶",
            expend=None,
            owner=user,
            enable=True,
        )
        tag_mapping.tags.add(tag)
        Expense.objects.create(
            key="十月",
            expend=account,
            owner=user,
            enable=True,
        )

        parsed = single_parse_transaction(
            _expense_row(commodity="十月结晶会员十月购物"),
            user.id,
            _parse_config(),
            "十月结晶",
        )

        assert parsed["expense"] == EXPENSES_OTHER
        assert parsed["selected_expense_key"] == "十月结晶"
        assert parsed["tag"] == "#ManualTag"


@pytest.mark.django_db
class TestIncomeMappingTagsWithoutAccount:
    @patch("project.apps.translate.services.handlers.get_default_assets")
    def test_tag_applied_with_fallback_income_account(self, mock_assets, user):
        mock_assets.return_value = _default_assets()
        tag = Tag.objects.create(name="Bonus", owner=user)
        mapping = Income.objects.create(
            key="工资",
            income=None,
            owner=user,
            enable=True,
        )
        mapping.tags.add(tag)

        parsed = single_parse_transaction(
            _income_row(commodity="工资到账"),
            user.id,
            _parse_config(),
            None,
        )

        assert parsed["expense"] == INCOME_OTHER
        assert parsed["selected_expense_key"] == "工资"
        assert parsed["tag"] == "#Bonus"

    @patch("project.apps.translate.services.handlers.get_default_assets")
    def test_manual_selected_key_without_income_account(self, mock_assets, user):
        mock_assets.return_value = _default_assets()
        tag = Tag.objects.create(name="SideIncome", owner=user)
        income_account = Account.objects.create(account="Income:Salary", owner=user)

        tag_mapping = Income.objects.create(
            key="兼职",
            income=None,
            owner=user,
            enable=True,
        )
        tag_mapping.tags.add(tag)
        Income.objects.create(
            key="工资",
            income=income_account,
            owner=user,
            enable=True,
        )

        parsed = single_parse_transaction(
            _income_row(commodity="工资与兼职收入"),
            user.id,
            _parse_config(),
            "兼职",
        )

        assert parsed["expense"] == INCOME_OTHER
        assert parsed["selected_expense_key"] == "兼职"
        assert parsed["tag"] == "#SideIncome"


@pytest.mark.django_db
class TestPayeeWithoutAccountMapping:
    def test_payee_from_mapping_without_account(self, user):
        Expense.objects.create(
            key="十月结晶",
            payee="十月结晶官方",
            expend=None,
            owner=user,
            enable=True,
        )
        row = _expense_row()
        handler = PayeeHandler(row)
        assert handler.get_payee(row, user.id, selected_mapping_key=None) == "十月结晶官方"
