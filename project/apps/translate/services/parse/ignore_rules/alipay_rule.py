# project/apps/translate/services/parse/rules/alipay_rule.py
from project.apps.translate.services.parse.ignore_registry import registry
from project.apps.translate.utils import BILL_ALI
from project.apps.translate.utils import pattern
from typing import Dict
import re


def alipay_pre_filter(row: Dict, args: Dict) -> bool:
    """支付宝预过滤规则

    只有返回为True时，才会忽略该行数据
    """
    # 移除"退款成功"，因为支付宝中的退款往往是单独一行，且对应支出也是单独一行会被记录，所以需要退款记录进行冲抵
    if row['transaction_status'] in ["交易关闭", "解冻成功", "信用服务使用成功", "已关闭", "还款失败", "等待付款", "芝麻免押下单成功"]:
        return True
    elif re.match(pattern["余额宝"], row['commodity']):
        return True
    else:
        return False

def alipay_fund_pre_filterv(row: Dict, args: Dict) -> bool:
    """余额宝预过滤规则"""
    return row['commodity'] in ["转账收款到余额宝", "余额宝-自动转入", "余额宝-单次转入"]


# 注册规则
# registry.register_pre_filter(BILL_ALI, alipay_fund_pre_filterv)
registry.register_pre_filter(BILL_ALI, alipay_pre_filter)
