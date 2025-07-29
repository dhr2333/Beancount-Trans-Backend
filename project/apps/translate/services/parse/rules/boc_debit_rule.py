# project/apps/translate/services/parse/rules/boc_debit_rule.py
from project.apps.translate.services.parse.ignore_registry import registry
from project.apps.translate.utils import BILL_BOC_DEBIT
from typing import Dict


def boc_debit_pre_filter(row: Dict, args: Dict) -> bool:
    """中国银行借记卡预过滤规则

    只有返回为True时，才会忽略该行数据
    """
    if args['boc_debit_ignore'] is True:
        return ("支付宝" in row['counterparty'] or "财付通" in row['counterparty'])


# 注册规则
registry.register_pre_filter(BILL_BOC_DEBIT, boc_debit_pre_filter)
