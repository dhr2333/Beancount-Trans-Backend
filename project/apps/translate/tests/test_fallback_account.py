"""兜底账户解析测试。"""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from project.apps.translate.services.handlers import AccountHandler
from project.apps.translate.services.parse.transaction_parser import single_parse_transaction
from project.apps.translate.utils import BILL_ALI, DEFAULT_FALLBACK_ACCOUNT, get_fallback_account
from project.apps.translate.views.AliPay import alipay_get_balance_account


def _family_card_row(**overrides):
    row = {
        "transaction_time": "2024-02-25 20:01:48",
        "transaction_category": "母婴亲子",
        "counterparty": "十月**店",
        "commodity": "【天猫U先】十月结晶会员尊享精致妈咪出行必备生活随心包4件套 等多件",
        "transaction_type": "/",
        "amount": 14.8,
        "payment_method": "亲情卡(凯义(王凯义))",
        "transaction_status": "交易成功",
        "notes": "/",
        "bill_identifier": BILL_ALI,
        "uuid": "2024022522001174561439593142",
        "discount": False,
    }
    row.update(overrides)
    return row


def _parse_config(**overrides):
    defaults = {
        "ai_model": "None",
        "deepseek_apikey": None,
        "flag": "*",
        "reconciliation_fallback_account": "Equity:Custom-Fallback",
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class TestGetFallbackAccount:
    def test_none_config_returns_default(self):
        assert get_fallback_account(None) == DEFAULT_FALLBACK_ACCOUNT

    def test_empty_field_returns_default(self):
        config = SimpleNamespace(reconciliation_fallback_account=None)
        assert get_fallback_account(config) == DEFAULT_FALLBACK_ACCOUNT

    def test_custom_account(self):
        config = SimpleNamespace(reconciliation_fallback_account="Equity:Custom-Fallback")
        assert get_fallback_account(config) == "Equity:Custom-Fallback"


class TestAlipayGetBalanceAccount:
    def test_family_card_uses_fallback_account(self):
        data = _family_card_row()
        handler = AccountHandler(data)
        handler.type = data["commodity"]

        assets = {
            "ALIPAY": "Assets:Digital:Alipay",
            "ALIFUND": "Assets:Digital:Alifund",
        }
        account = alipay_get_balance_account(
            handler,
            data,
            assets,
            ownerid=1,
            fallback_account="Equity:Custom-Fallback",
        )
        assert account == "Equity:Custom-Fallback"


@pytest.mark.django_db
class TestFamilyCardParseUsesFallbackAccount:
    @patch("project.apps.translate.services.handlers.get_default_assets")
    @patch("project.apps.translate.services.handlers.get_mapping_provider")
    def test_uses_configured_fallback_account(self, mock_provider, mock_assets, user):
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

        parsed = single_parse_transaction(
            _family_card_row(),
            user.id,
            _parse_config(reconciliation_fallback_account="Equity:Custom-Fallback"),
            None,
        )
        assert parsed["account"] == "Equity:Custom-Fallback"

    @patch("project.apps.translate.services.handlers.get_default_assets")
    @patch("project.apps.translate.services.handlers.get_mapping_provider")
    def test_empty_fallback_uses_default(self, mock_provider, mock_assets, user):
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

        parsed = single_parse_transaction(
            _family_card_row(),
            user.id,
            _parse_config(reconciliation_fallback_account=None),
            None,
        )
        assert parsed["account"] == DEFAULT_FALLBACK_ACCOUNT
