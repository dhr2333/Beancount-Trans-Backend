# project/apps/translate/services/parse/rules/cmb_credit_rule.py
from project.apps.translate.services.parse.ignore_registry import registry
from project.apps.translate.utils import BILL_CMB_CREDIT
from typing import Dict


def cmb_credit_pre_filter(row: Dict, args: Dict) -> bool:
    """CMB信用卡预过滤规则

    只有返回为True时，才会忽略该行数据
    """
    if args['cmb_credit_ignore'] is True:
        return "支付宝" in row['counterparty'] or "财付通" in row['counterparty']
    else:
        return False

def cmb_credit_post_filter(entry: Dict, args: Dict) -> bool:
    """CMB信用卡后过滤规则"""
    # 后过滤逻辑实现
    return False

# 注册规则
registry.register_pre_filter(BILL_CMB_CREDIT, cmb_credit_pre_filter)
registry.register_post_filter(BILL_CMB_CREDIT, cmb_credit_post_filter)
