import re
from datetime import time
from .models import Assets
from abc import ABC, abstractmethod

BILL_ALI = "alipay"
BILL_WECHAT = "wechat"
BILL_CMB_CREDIT = "CMB_Credit"
BILL_BOC_DEBIT = "BOC_Debit"
BILL_ICBC_DEBIT = "ICBC_Debit"
BILL_CCB_DEBIT = "CCB_Debit"

ASSETS_OTHER = "Assets:Other"
EXPENSES_OTHER = "Expenses:Other"  # 无法分类的支出
INCOME_OTHER = "Income:Other"
OPENBALANCE = "Equity:OpenBalance"

TIME_BREAKFAST_START = time(6)
TIME_BREAKFAST_END = time(10)
TIME_LUNCH_START = time(10)
TIME_LUNCH_END = time(14)
TIME_DINNER_START = time(16)
TIME_DINNER_END = time(20)

pattern = {"余额宝": r'^余额宝.*收益发放$',
           "花呗主动还款": r'^花呗主动还款.*账单$',
           "花呗自动还款": r'^花呗自动还款.*账单$',
           "基金": r'.*-卖出至.*'
           }  # 统一管理正则表达式

transaction_status = {
    "wechatpay": ["支付成功", "已存入零钱", "已转账", "对方已收钱", "已到账", "已全额退款", "对方已退还", "提现已到账",
                  "充值完成", "充值成功", "已收钱"],
    "alipay": ["交易成功", "交易关闭", "退款成功", "支付成功", "代付成功", "还款成功", "还款失败", "已关闭", "解冻成功",
               "信用服务使用成功", "等待付款"]
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


class InitStrategy(ABC):
    @abstractmethod
    def init(self, bill, **kwargs):
        pass


class FormatData:

    def format_instance(entry):
        ignore_data = IgnoreData(None)
        formatted_str = ""

        formatted_str += f"{entry['date']}"
        formatted_str += f" *"
        formatted_str += f" \"{entry['payee']}\""
        formatted_str += f" \"{entry['note']}\""
        if entry['tag'] is not None:
            formatted_str += f" {entry['tag']}"
        formatted_str += f"\n    time: \"{entry['time']}\"\n"
        if entry['uuid'] is not None:
            formatted_str += f"    uuid: \"{entry['uuid']}\"\n"
        formatted_str += f"    status: \"{entry['status']}\"\n"
        formatted_str += f"    {entry['expense']} {entry['expenditure_sign']}{entry['amount']} CNY\n"
        formatted_str += f"    {entry['account']} {entry['account_sign']}"
        if ignore_data.notes(entry):
            formatted_str += f"{entry['actual_amount']} CNY"
        else:
            formatted_str += f"{entry['amount']} CNY"

        if ignore_data.notes(entry):
            formatted_str += "\n    Expenses:Finance:Commission"

        return formatted_str + "\n\n"
    
    def balance_instance(entry):
        formatted_str = ""

        formatted_str += f"{entry['balance_date']}"
        formatted_str += f" balance"
        formatted_str += f" {entry['account']}"
        formatted_str += f" {entry['balance']} CNY"
        formatted_str += f"\n{entry['date']}"
        formatted_str += f" pad"
        formatted_str += f" {entry['account']}"
        formatted_str += f" Assets:Other"

        return formatted_str + "\n\n"
    
    def installment_instance(entry):
        formatted_str = ""
        
        formatted_str += f"{entry['date']}"
        formatted_str += f" #"
        formatted_str += f" \"{entry['payee']}"
        formatted_str += f" ["
        formatted_str += f"{entry['installment_granularity']}"
        formatted_str += f" REPEAT"
        formatted_str += f" {entry['installment_cycle']}"
        formatted_str += f" TIMES]\""
        formatted_str += f"\n    time: \"{entry['time']}\"\n"
        if entry['uuid'] is not None:
            formatted_str += f"    uuid: \"{entry['uuid']}\"\n"
        formatted_str += f"    status: \"{entry['status']}\"\n"
        formatted_str += f"    {entry['expense']}"
        formatted_str += f" {entry['expenditure_sign']}"
        formatted_str += f" {float(entry['amount'])/float(entry['installment_cycle']):.2f} CNY\n"
        formatted_str += f"    {entry['account']} {entry['account_sign']}"
        formatted_str += f"{float(entry['amount'])/float(entry['installment_cycle']):.2f} CNY"
        
        
        return formatted_str + "\n\n"


class IgnoreData:
    def __init__(self, data):
        self.data = data

    def empty(self, data):
        return data == {}

    def notes(self, data):
        return data["note"] == "零钱提现"
    
    def balance(self, data):
        from datetime import datetime

        # 将字符串日期转换为 datetime 对象
        for record in data:
            record["transaction_time"] = datetime.strptime(record["transaction_time"], "%Y-%m-%d %H:%M:%S")
        # 以天为单位找到每组中时间最晚的记录
        unique_days = {}
        for record in data:
            date_key = record["transaction_time"].date()
            if date_key not in unique_days or record["transaction_time"] > unique_days[date_key]["transaction_time"]:
                unique_days[date_key] = record
        # 提取结果并保证输入和输出的格式不变
        result = list(unique_days.values())
        # 将 transaction_time 转换回字符串
        for record in result:
            record["transaction_time"] = record["transaction_time"].strftime("%Y-%m-%d %H:%M:%S")
        # 输出结果
        return result


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

