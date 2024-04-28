# /home/daihaorui/账单案例/统一账单/工商银行储蓄卡.pdf
import re
from datetime import time
from .models import Assets

BILL_ALI = "alipay"
BILL_WECHAT = "wechat"
BILL_CMB_CREDIT = "CMB_Credit"
BILL_BOC_DEBIT = "BOC_Debit"
BILL_ICBC_DEBIT = "ICBC_Debit"
BILL_CCB_DEBIT = "CCB_Debit"

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
        if data[9] == BILL_ALI and data[7] in ["退款成功", "交易关闭", "解冻成功", "信用服务使用成功", "已关闭",
                                               "还款失败"]:
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

    def cmb_credit(self, data, cmb_credit_ignore):
        if data[9] == BILL_CMB_CREDIT and "支付宝" in data[2] or "财付通" in data[2]:
            return cmb_credit_ignore == "True"


def get_card_number(content, sourcefile_identifier):
    from translate.views.BOC_Debit import boc_debit_sourcefile_identifier, boc_debit_get_card_number
    from translate.views.ICBC_Debit import icbc_debit_sourcefile_identifier, icbc_debit_get_card_number
    """
    从账单文件中获取该账单对应的银行卡号
    """
    if sourcefile_identifier == boc_debit_sourcefile_identifier:
        card_number = boc_debit_get_card_number(content)
    elif sourcefile_identifier == icbc_debit_sourcefile_identifier:
        card_number = icbc_debit_get_card_number(content)
    return card_number


def card_number_get_key(data):
    """
    从银行卡号获取后四位尾号
    """
    return re.search(r'\d{4}$', data).group()
