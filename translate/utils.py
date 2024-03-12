# import logging
#
# from datetime import datetime, time
#
# from django.http import JsonResponse
# from django.shortcuts import render
# from django.views import View
#
# from mydemo import settings
# from mydemo.utils.file import create_temporary_file, init_project_file
# from mydemo.utils.token import get_token_user_id
# from .models import Expense, Assets, Income
# from translate.views.AliPay import AliPayStrategy
# from translate.views.WeChat import WeChatPayStrategy
import re
from datetime import time

from .models import Assets

# ALIPAY = None
# ALIFUND = None
# HUABEI = None
# WECHATPAY = None  # Assets表中微信零钱的默认值，get_default_assets()函数会对其进行初始化
# WECHATFUND = None

BILL_ZHAOSHANG = "Credit_ZhaoShang"
BILL_ALI = "alipay"
BILL_WECHAT = "wechat"

ASSETS_OTHER = "Assets:Other"
EXPENSES_OTHER = "Expenses:Other"  # 无法分类的支出
INCOME_OTHER = "Income:Other"

TIME_BREAKFAST_START = time(6)
TIME_BREAKFAST_END = time(10)
TIME_LUNCH_START = time(10)
TIME_LUNCH_END = time(14)
TIME_DINNER_START = time(16)
TIME_DINNER_END = time(20)

pattern = {"余额宝": r'^余额宝.*收益发放$',
           "花呗": r'^花呗主动还款.*账单$',
           "基金": r'.*-卖出至.*'
           }  # 统一管理正则表达式


transaction_status = {
    "wechatpay": ["支付成功", "已存入零钱", "已转账", "对方已收钱", "已到账", "已全额退款", "对方已退还", "提现已到账",
                  "充值完成", "充值成功", "已收钱"],
    "alipay": ["交易成功", "交易关闭", "退款成功", "支付成功", "代付成功", "还款成功", "还款失败", "已关闭", "解冻成功",
               "信用服务使用成功"]
}


def get_default_assets(ownerid):
    """
    获取登录账号的资产账户的默认值
    :param ownerid: 用户id
    :return: None
    """
    default_assets = {
        "微信零钱": "WECHATPAY",
        "微信零钱通": "WECHATFUND",
        "支付宝余额": "ALIPAY",
        "支付宝余额宝": "ALIFUND",
        "支付宝花呗": "HUABEI"
    }
    actual_assets = {}

    for asset_name, var_name in default_assets.items():
        asset = Assets.objects.filter(full=asset_name, owner_id=ownerid).first()
        globals()[var_name] = asset.assets if asset else ASSETS_OTHER
        actual_assets[var_name] = asset.assets if asset else ASSETS_OTHER
    return actual_assets


class PaymentStrategy:
    def get_data(self, bill):
        raise NotImplementedError()


class FormatData:
    def __init__(self, entry):
        self.entry = entry

    def commission(self, entry):
        instance = f"{entry['date']} * \"{entry['payee']}\" \"{entry['notes']}\"\n\
    time: \"{entry['time']}\"\n\
    uuid: \"{entry['uuid']}\"\n\
    status: \"{entry['status']}\"\n\
    {entry['expend']} {entry['expend_sign']}{entry['amount']}\n\
    {entry['account']} {entry['account_sign']}{entry['actual_amount']}\n\
    Expenses:Finance:Commission\n\n"
        return instance

    def default(self, entry):
        instance = f"{entry['date']} * \"{entry['payee']}\" \"{entry['notes']}\"\n\
    time: \"{entry['time']}\"\n\
    uuid: \"{entry['uuid']}\"\n\
    status: \"{entry['status']}\"\n\
    {entry['expend']} {entry['expend_sign']}{entry['amount']}\n\
    {entry['account']} {entry['account_sign']}{entry['amount']}\n\n"
        return instance


class IgnoreData:
    def __init__(self, data):
        self.data = data

    def wechatpay(self, data):
        if data[9] == BILL_WECHAT:
            return data[7] in ["已全额退款", "对方已退还"] or data[7].startswith("已退款")

    def alipay(self, data):
        if data[9] == BILL_ALI and data[7] in ["退款成功", "交易关闭", "解冻成功", "信用服务使用成功", "已关闭", "还款失败"]:
            return True
        elif re.match(pattern["余额宝"], data[3]):
            return True
        else:
            return False

    def alipay_fund(self, data):
        return data[1] in ["转账收款到余额宝", "余额宝-自动转入", "余额宝-单次转入"]

    def empty(self, data):
        return data == {}

    def notes(self, data):
        return data["notes"] == "零钱提现"

    def credit_zhaoshang(self, data, zhaoshang_ignore):
        if data[9] == BILL_ZHAOSHANG and "支付宝" in data[2] or "财付通" in data[2]:
            return zhaoshang_ignore == "True"


class UnsupportedFileType(Exception):
    pass
