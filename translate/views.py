import csv
import os
import re
from datetime import datetime

from django.db.models import Max
from django.http import JsonResponse
from django.shortcuts import render
from django.views import View

from mydemo import settings
from mydemo.utils.file import create_temporary_file, init_project_file
from mydemo.utils.token import get_token_user_id
from .models import Expense, Assets
from .utils import *

EXPENSES_OTHER = "Expenses:Other"  # 无法分类的支出
INCOME_OTHER = "Income:Other"
ASSETS_OTHER = "Assets:Other"

WECHATPAY = None  # Assets表中微信零钱的默认值，get_default_assets()函数会对其进行初始化
WECHATFUND = None
ALIPAY = None
ALIFUND = None

BILL_WECHAT = "wechat"  # 用于判断账单类型
BILL_ALI = "alipay"


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
        "支付宝余额宝": "ALIFUND"
    }

    for asset_name, var_name in default_assets.items():
        asset = Assets.objects.filter(full=asset_name, owner_id=ownerid).first()
        globals()[var_name] = asset.income if asset else ASSETS_OTHER


def get_uuid(data):
    uuid = None
    if data[9] == "wechat":
        uuid = data[10].rstrip("\t")
    elif data[9] == "alipay":
        uuid = data[10]
    return uuid


def get_amount(data):
    if data[9] == "alipay":
        amount = "{:.2f} CNY".format(float(data[5]))  # 支付宝账单格式为"10.00"，直接以数字形式返回即可
    elif data[9] == "wechat":
        amount = "{:.2f} CNY".format(float(data[5][1:]))  # 微信账单格式为"￥10.00"，需要转换
    return amount


def calculate_commission(total, commission):
    if commission != "":
        amount = "{:.2f} CNY".format(float(total.split()[0]) - float(commission.split()[0]))
    else:
        amount = total
    return amount


def get_payee(data):
    payee = data[2]
    notes = data[3]
    key_list = list(Expense.objects.values_list('key', flat=True))
    if data[4] == "/" and data[9] == "wechat":  # 一般微信好友转账，如妈妈->我
        payee = data[6][:4]
    elif data[1] == "微信红包（单发）":
        payee = payee[2:]
    elif data[1] == "转账-退款":
        payee = "退款"
    elif data[1] == "微信红包-退款":
        payee = "退款"
    elif '(' in payee and ')' in payee and data[9] == "alipay":
        match = re.search(r'\((.*?)\)', payee)  # 提取 account 中的数字部分
        if match:
            payee = match.group(1)
    else:
        matching_keys = [k for k in key_list if k in payee or k in notes]  # 获取所有匹配的key,用于判断优先级
        max_order = None
        for matching_key in matching_keys:
            expend_instance = Expense.objects.filter(key__contains=matching_key).aggregate(
                max_order=Max('payee_order'))
            matching_max_order = expend_instance['max_order']
            if matching_max_order is not None and (max_order is None or matching_max_order > max_order):
                max_order = matching_max_order
                expend_instance = Expense.objects.filter(key__contains=matching_key, payee_order=max_order).first()
                if expend_instance is not None and expend_instance.payee is not None:
                    payee = expend_instance.payee
        if payee == "" and data[9] == "alipay":
            payee = data[2]
            return payee
        elif payee == "" and data[9] == "wechat":
            payee = data[2]
            if payee == "/":
                payee = data[1]
        return payee
    return payee


def get_notes(data):
    notes = None
    if data[9] == "wecaht" and data[4] == "/":
        notes = data[1]
    else:
        notes = data[3]
    return notes


def get_shouzhi(shouzhi):
    expend_sign = None
    account_sign = None
    if shouzhi == "支出":
        expend_sign = "+"
        account_sign = "-"
    elif shouzhi == "收入":
        expend_sign = "-"
        account_sign = "+"
    elif shouzhi in ["/", "不计收支"]:
        expend_sign = "-"
        account_sign = "+"
    return expend_sign, account_sign


class GetExpense:
    def __init__(self, data):
        self.key_list = None
        self.type = None
        self.expend = EXPENSES_OTHER
        self.bill = data[9]
        self.balance = data[4]

    def initialize_type(self, data):
        if self.bill == BILL_WECHAT:
            self.type = data[1][:5]
        elif self.bill == BILL_ALI:
            self.type = data[3]

    def initialize_key_list(self, ownerid):
        if self.balance == "支出":
            self.key_list = Expense.objects.filter(owner_id=ownerid).values_list('key', flat=True)
        elif self.balance == "收入":
            self.key_list = None
        elif self.balance == "/" or self.balance == "不计收支":
            self.key_list = Assets.objects.filter(owner_id=ownerid).values_list('key', flat=True)

    def get_expense(self, data, ownerid):
        self.initialize_key_list(ownerid)  # 根据收支情况获取数据库中key的所有值，将其处理为列表
        self.initialize_type(data)
        expend = self.expend

        if self.balance == "支出":
            for key in self.key_list:
                if key in data[2] or key in data[3]:
                    expend_instance = Expense.objects.get(key=key)
                    expend = expend_instance.expend
                    return expend
            expend = EXPENSES_OTHER
        elif self.balance == "收入":
            expend = INCOME_OTHER
        elif self.balance == "/" or self.balance == "不计收支":
            if self.bill == BILL_WECHAT:
                expend = self.wechatpay_expense(data)
            elif self.bill == BILL_ALI:
                expend = self.alipay_expense(data)
        return expend

    def wechatpay_expense(self, data):
        expend = "Unknown-WechatPay"

        if self.type == "零钱提现":
            expend = WECHATPAY
        elif self.type == "零钱充值":
            for key in self.key_list:
                if key in data[2]:
                    expend_instance = Assets.objects.get(key=key)
                    expend = expend_instance.income
                    return expend
            expend = ASSETS_OTHER
        elif self.type == "零钱通转出":
            expend = WECHATFUND
        elif self.type == "转入零钱通":
            index = data[1].find("来自")
            result = data[1][index + 2:]  # 取来自之后的所有数据，例如"建设银行(5522)"
            for key in self.key_list:
                if key in result:
                    expend_instance = Assets.objects.get(key=key)
                    expend = expend_instance.income
                    return expend
            expend = ASSETS_OTHER
        return expend

    def alipay_expense(self, data):
        expend = "Unknown-AliPay"

        if self.type == "转账收款到余额宝":
            expend = ALIPAY
        elif self.type == "余额宝-自动转入":
            expend = ALIPAY
        elif self.type == "余额宝-转出到余额":
            expend = ALIFUND
        elif self.type == "余额宝-单次转入":
            result = data[6]
            for key in self.key_list:
                if key in result:
                    expend_instance = Assets.objects.get(key=key)
                    expend = expend_instance.income
                    return expend
                else:
                    expend = ASSETS_OTHER
        elif self.type == "余额宝-转出到银行卡":
            expend = ALIFUND
        elif self.type == "充值-普通充值":
            expend = ASSETS_OTHER  # 支付宝账单中银行卡充值到余额时没有任何银行的信息，需要手动对账
        elif self.type == "提现-实时提现":
            expend = ALIPAY
        else:
            expend = ASSETS_OTHER
        return expend


class GetAccount:
    def __init__(self, data):
        self.key = None
        self.key_list = None
        self.type = None
        self.account = ASSETS_OTHER
        self.bill = data[9]
        self.balance = data[4]

    def initialize_type(self, data):
        if self.bill == BILL_WECHAT:
            self.type = data[1][:5]
        elif self.bill == BILL_ALI:
            self.type = data[3]

    def initialize_key_list(self, ownerid):
        self.key_list = Assets.objects.filter(owner_id=ownerid).values_list('key', flat=True)

    def initialize_key(self, data):
        self.key = data[6]
        if "&" in self.key:  # 该判断用于解决支付宝中"&[红包]"导致无法被匹配的问题
            sub_strings = self.key.split("&")
            self.key = sub_strings[0]

    def get_account(self, data, ownerid):
        self.initialize_key(data)
        self.initialize_key_list(ownerid)  # 根据收支情况获取数据库中key的所有值，将其处理为列表
        self.initialize_type(data)
        account = self.account
        key = self.key
        # print("get_account(self, data, ownerid) = ",self.key_list)

        if self.balance == "收入" or self.balance == "支出":  # 收/支栏 值为"收入"或"支出"
            if key in self.key_list:
                # account_instance = Assets.objects.get(key=key)
                account_instance = Assets.objects.filter(key=key, owner_id=ownerid).first()
                account = account_instance.income
                return account
            elif key == "" and self.bill == BILL_ALI:  # 第三方平台到支付宝的收入
                account = ALIPAY
            else:
                if '(' in key and ')' in key:
                    digits = key.split('(')[1].split(')')[0]  # 提取 account 中的数字部分
                    # 判断提取到的数字是否在列表中
                    if digits in self.key_list:
                        # print("digits = ", digits,"self.key_list = ", self.key_list)
                        account_instance = Assets.objects.filter(key=digits, owner_id=ownerid).first()
                        # print("account_instance = ", account_instance)
                        account = account_instance.income
                        return account
                    else:
                        return ASSETS_OTHER
        elif self.balance == "/" or self.balance == "不计收支":  # 收/支栏 值为/
            if self.bill == BILL_WECHAT:
                account = self.wechatpay_account(data, ownerid)
            elif self.bill == BILL_ALI:
                account = self.alipay_account(data, ownerid)
        return account

    def wechatpay_account(self, data, ownerid):
        if self.type == "零钱提现":
            for key in self.key_list:
                if key in data[2]:
                    account_instance = Assets.objects.filter(key=key, owner_id=ownerid).first()
                    account = account_instance.income
                    return account
            account = ASSETS_OTHER
        elif self.type == "零钱充值":
            account = WECHATPAY
        elif self.type == "零钱通转出":
            index = data[1].find("到")
            result = data[1][index + 1:]  # 取来自之后的所有数据，例如"建设银行(5522)"
            for key in self.key_list:
                if key in result:
                    account_instance = Assets.objects.filter(key=key, owner_id=ownerid).first()
                    account = account_instance.income
                    return account
            account = ASSETS_OTHER
        elif self.type == "转入零钱通":
            account = WECHATFUND
        return account

    def alipay_account(self, data, ownerid):
        if self.type == "转账收款到余额宝":
            account = ALIFUND
        elif self.type == "余额宝-自动转入":
            account = ALIFUND
        elif self.type == "余额宝-转出到余额":
            account = ALIPAY
        elif self.type == "余额宝-单次转入":
            account = ALIFUND
        elif self.type == "余额宝-转出到银行卡":
            result = data[6]
            for key in self.key_list:
                if key in result:
                    account_instance = Assets.objects.filter(key=key, owner_id=ownerid).first()
                    account = account_instance.income
                    return account
            account = ASSETS_OTHER
        elif self.type == "充值-普通充值":
            account = ALIPAY  # 支付宝账单中银行卡充值到余额时没有任何银行的信息，需要手动对账
        elif self.type == "提现-实时提现":
            # TODO
            # 可以利用账单中的"交易对方"与数据库中的"full"进行对比，若被包含可直接匹配income
            account = ASSETS_OTHER  # 支付宝账单中提现最大颗粒度只到具体银行，若该银行有两张银行卡便有问题，需要手动对账
        else:
            account = ASSETS_OTHER
        return account


def format(data, owner_id):
    """
        date : 日期         2023-04-28
        time : 时间         09:03:00
        uuid : 交易单号     1000039801202211266356238708041
        amount : 金额        23.00 CNY
        payee : 收款方      浙江古茗
        notes : 备注        商品详情
        expend : 支付方式   Expenses:Food:DrinkFruit
        account : 账户      Liabilities:CreditCard:Bank:ZhongXin:C6428
    """
    date = datetime.strptime(data[0], "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d")
    time = datetime.strptime(data[0], "%Y-%m-%d %H:%M:%S").strftime("%H:%M:%S")
    uuid = get_uuid(data)
    amount = get_amount(data)
    payee = get_payee(data)
    notes = get_notes(data)
    expend_sign, account_sign = get_shouzhi(data[4])
    expend = GetExpense(data).get_expense(data, owner_id)
    account = GetAccount(data).get_account(data, owner_id)
    commission = data[8][4:]
    if data[4] == "/":
        actual_amount = calculate_commission(amount, commission)
        return {"date": date, "time": time, "uuid": uuid, "payee": payee, "notes": notes, "expend": expend,
                "expend_sign": expend_sign,
                "account": account, "account_sign": account_sign, "amount": amount, "actual_amount": actual_amount}
    return {"date": date, "time": time, "uuid": uuid, "payee": payee, "notes": notes, "expend": expend,
            "expend_sign": expend_sign,
            "account": account, "account_sign": account_sign, "amount": amount}


def beancount_outfile(data, owner_id: int, write=False):
    """对账单数据进行过滤并格式化

    Args:
        data (file): 账单数据
        owner_id (int): 用户id
        write (bool, optional): 是否写入，默认为False

    Returns:
        list: 格式化后的账单数据
    """
    instance_list = []
    for row in data:
        if row[7] != "交易成功":
            continue
        if row[2] == "兴全基金管理有限公司" or row[6] == "亲情卡(凯义(王凯义))":  # 忽略余额宝收益，最后做balance结余断言时统一归于基金收益
            continue
        entry = format(row, owner_id)
        if entry == {}:
            continue
        elif entry["notes"] == "零钱提现":
            instance = \
                f"{entry['date']} * \"{entry['payee']}\" \"{entry['notes']}\"\n\
    time: \"{entry['time']}\"\n\
    uuid: \"{entry['uuid']}\"\n\
    {entry['expend']} {entry['expend_sign']}{entry['amount']}\n\
    {entry['account']} {entry['account_sign']}{entry['actual_amount']}\n\
    Expenses:Finance:Commission\n\n"
        else:
            instance = \
                f"{entry['date']} * \"{entry['payee']}\" \"{entry['notes']}\"\n\
    time: \"{entry['time']}\"\n\
    uuid: \"{entry['uuid']}\"\n\
    {entry['expend']} {entry['expend_sign']}{entry['amount']}\n\
    {entry['account']} {entry['account_sign']}{entry['amount']}\n\n"
        instance_list.append(instance)
        if write:
            mouth, year = instance[5:7], instance[0:4]
            file = os.path.join(os.path.dirname(settings.BASE_DIR), "Beancount-Trans-Assets", year,
                                f"{mouth}-expenses.bean")
            init_project_file(file)
            with open(file, mode='a') as file:
                file.write(instance)
    return instance_list


class AnalyzeView(View):
    def post(self, request):
        owner_id = get_token_user_id(request)  # 根据前端传入的JWT Token获取owner_id,如果是非认证用户或者Token过期则返回1(默认用户)
        uploaded_file = request.FILES.get('trans', None)  # 获取前端传入的文件
        temp, encoding = create_temporary_file(uploaded_file)  # 创建临时文件并获取文件编码

        with open(temp.name, newline='', encoding=encoding, errors="ignore") as csvfile:
            list = get_initials_bill(bill=csv.reader(csvfile))
        get_default_assets(ownerid=owner_id)
        format_list = beancount_outfile(list, owner_id, write=False)

        os.unlink(temp.name)
        return JsonResponse(format_list, safe=False, content_type='application/json')

    def get(self, request):
        title = "trans"
        context = {"title": title}
        return render(request, "translate/trans.html", context)
