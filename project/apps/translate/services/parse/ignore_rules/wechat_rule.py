# project/apps/translate/services/parse/rules/wechat_rule.py
from project.apps.translate.services.parse.ignore_registry import registry
from project.apps.translate.utils import BILL_WECHAT
from typing import Dict


def wechatpay_pre_filter(row: Dict, args: Dict) -> bool:
    """微信支付预过滤规则

    只有返回为True时，才会忽略该行数据
    """
    return row["transaction_status"] in ["已全额退款", "对方已退还"]


# 注册规则
registry.register_pre_filter(BILL_WECHAT, wechatpay_pre_filter)
