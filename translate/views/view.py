import csv
import os
from datetime import datetime

from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.views import View
from mydemo import settings
from mydemo.utils.exceptions import UnsupportedFileType, DecryptionError
from mydemo.utils.file import create_temporary_file, init_project_file, pdf_convert_to_csv
from mydemo.utils.token import get_token_user_id
from translate.models import Expense, Income
from translate.utils import *
from translate.views.AliPay import *
from translate.views.BOC_Debit import *
from translate.views.CMB_Credit import *
from translate.views.ICBC_Debit import *
from translate.views.WeChat import *


class AnalyzeView(View):
    def post(self, request):
        args = {"cmb_credit_ignore": request.POST.get('cmb_credit_ignore'), "write": request.POST.get('write'),
                "password": request.POST.get('password')}
        owner_id = get_token_user_id(request)  # 根据前端传入的JWT Token获取owner_id,如果是非认证用户或者Token过期则返回1(默认用户)
        uploaded_file = request.FILES.get('trans', None)  # 获取前端传入的文件
        try:
            csv_file = pdf_convert_to_csv(uploaded_file, args["password"])  # 对文件格式进行判断并转换
        except DecryptionError:
            return HttpResponse("Decryption failed", status=403)
        temp, encoding = create_temporary_file(csv_file)  # 创建临时文件并获取文件编码

        try:
            with open(temp.name, newline='', encoding=encoding, errors="ignore") as csvfile:
                list = get_initials_bill(bill=csv.reader(csvfile))
            format_list = beancount_outfile(list, owner_id, args)
        except UnsupportedFileType as e:
            return JsonResponse({'error': str(e)}, status=400)

        os.unlink(temp.name)
        return JsonResponse(format_list, safe=False, content_type='application/json')

    def get(self, request):
        title = "trans"
        context = {"title": title}
        return render(request, "translate/trans.html", context)


def get_initials_bill(bill):
    """Get the initials of the bill's name."""
    first_line = next(bill)[0]
    year = first_line[:4]
    try:
        card_number = card_number_get_key(first_line)
    except:
        pass
    if isinstance(first_line, str) and alipay_csvfile_identifier in first_line:
        strategy = AliPayStrategy()
    elif isinstance(first_line, str) and wechat_csvfile_identifier in first_line:
        strategy = WeChatPayStrategy()
    elif isinstance(first_line, str) and cmb_credit_csvfile_identifier in first_line:
        strategy = CmbCreditStrategy()
        return strategy.get_data(bill, year)
    elif isinstance(first_line, str) and boc_debit_csvfile_identifier in first_line:
        strategy = BocDebitStrategy()
        return strategy.get_data(bill, card_number)
    elif isinstance(first_line, str) and icbc_debit_csvfile_identifier in first_line:
        strategy = IcbcDebitStrategy()
        return strategy.get_data(bill, card_number)
    else:
        raise UnsupportedFileType("当前账单不支持")
    return strategy.get_data(bill)


def beancount_outfile(data, owner_id: int, args):
    """对账单数据进行过滤并格式化

    Args:
        data (file): 账单数据
        owner_id (int): 用户id
        args (dict): 前端上传的可选选项

    Returns:
        list: 格式化后的账单数据
    """
    ignore_data = IgnoreData(None)
    instance_list = []
    for row in data:
        # print(row)
        if ignore_data.alipay(row):
            continue
        elif ignore_data.alipay_fund(row):
            continue
        elif ignore_data.wechatpay(row):
            continue
        elif ignore_data.cmb_credit(row, args["cmb_credit_ignore"]):
            continue
        try:
            entry = format(row, owner_id)
            if ignore_data.empty(entry):
                continue
            elif ignore_data.notes(entry):  # 该条目只有微信零钱提现，支付宝提现功能不支持。支付宝账单不包含转出的银行卡信息
                instance = FormatData(entry).commission(entry)
            else:
                instance = FormatData(entry).default(entry)
            instance_list.append(instance)
            if args["write"] == "True":
                mouth, year = instance[5:7], instance[0:4]
                file = os.path.join(os.path.dirname(settings.BASE_DIR), "Beancount-Trans-Assets", year,
                                    f"{mouth}-expenses.bean")
                init_project_file(file)
                with open(file, mode='a') as file:
                    file.write(instance)
        except ValueError as e:
            instance = str(e) + "\n\n"
            instance_list.append(instance)
    return instance_list


def format(data, owner_id):
    """
        date : 日期         2023-04-28
        time : 时间         09:03:00
        uuid : 交易单号     1000039801202211266356238708041
        amount : 金额        23.00 CNY
        payee : 收款方      浙江古茗
        notes : 备注        商品详情
        expend : 支付方式   Expenses:Food:DrinkFruit
        account : 账户      Liabilities:CreditCard:Bank:CITIC:C6428
    """
    try:
        date = datetime.datetime.strptime(data[0], "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d")
        time = datetime.datetime.strptime(data[0], "%Y-%m-%d %H:%M:%S").strftime("%H:%M:%S")
        uuid = get_uuid(data)
        status = get_status(data)
        amount = get_amount(data)
        payee = GetPayee(data).get_payee(data, owner_id)
        notes = get_notes(data)
        expend_sign, account_sign = get_shouzhi(data)
        expend = GetExpense(data).get_expense(data, owner_id)
        account = GetAccount(data).get_account(data, owner_id)
        commission = data[8][4:]
        if data[4] == "/":
            actual_amount = calculate_commission(amount, commission)
            return {"date": date, "time": time, "uuid": uuid, "status": status, "payee": payee, "notes": notes,
                    "expend": expend,
                    "expend_sign": expend_sign,
                    "account": account, "account_sign": account_sign, "amount": amount, "actual_amount": actual_amount}
        return {"date": date, "time": time, "uuid": uuid, "status": status, "payee": payee, "notes": notes,
                "expend": expend,
                "expend_sign": expend_sign,
                "account": account, "account_sign": account_sign, "amount": amount}
    except ValueError as e:
        # logging.exception("format函数执行报错，可能是账单的格式有误")
        # logging.error("format函数执行报错，可能是账单的格式有误")
        # return "format函数执行报错，可能是账单的格式有误"
        raise e


class GetAccount:
    def __init__(self, data):
        self.key = None
        self.key_list = None
        self.full_list = None
        self.type = None
        self.account = ASSETS_OTHER
        self.bill = data[9]
        self.balance = data[4]

    def initialize_type(self, data):
        if self.bill == BILL_ALI:
            self.type = alipay_get_type(data)
        elif self.bill == BILL_WECHAT:
            self.type = wechatpay_get_type(data)

    def initialize_key_list(self, ownerid):
        self.key_list = Assets.objects.filter(owner_id=ownerid).values_list('key', flat=True)
        self.full_list = Assets.objects.filter(owner_id=ownerid).values_list('full', flat=True)

    def initialize_key(self, data):
        if self.bill == BILL_ALI:
            self.key = alipay_initalize_key(data)
        elif self.bill == BILL_WECHAT:
            self.key = wechatpay_initalize_key(self, data)
        elif self.bill == BILL_CMB_CREDIT:
            self.key = cmb_credit_init_key(data)
        elif self.bill == BILL_BOC_DEBIT:
            self.key = boc_debit_init_key(data)
        elif self.bill == BILL_ICBC_DEBIT:
            self.key = icbc_debit_init_key(data)

    def get_account(self, data, ownerid):
        self.initialize_key(data)
        self.initialize_key_list(ownerid)  # 根据收支情况获取数据库中key的所有值，将其处理为列表
        self.initialize_type(data)
        actual_assets = get_default_assets(ownerid=ownerid)
        account = self.account

        if self.balance == "收入":
            if self.bill == BILL_ALI:
                return alipay_get_income_account(self, actual_assets, ownerid)
            elif self.bill == BILL_WECHAT:
                return wechatpay_get_income_account(self, actual_assets, ownerid)
        elif self.balance == "支出":
            if self.bill == BILL_ALI:
                return alipay_get_expense_account(self, actual_assets, ownerid)
            elif self.bill == BILL_WECHAT:
                return wechatpay_get_expense_account(self, actual_assets, ownerid)
        elif self.balance == "/" or self.balance == "不计收支":  # 收/支栏 值为/
            if self.bill == BILL_ALI:
                return alipay_get_balance_account(self, data, actual_assets, ownerid)
            elif self.bill == BILL_WECHAT:
                return wechatpay_get_balance_account(self, data, actual_assets, ownerid)

        if self.bill == BILL_BOC_DEBIT:
            return boc_debit_get_account(self, ownerid)
        elif self.bill == BILL_CMB_CREDIT:
            return cmb_credit_get_account(self, ownerid)
        elif self.bill == BILL_ICBC_DEBIT:
            return icbc_debit_get_account(self, ownerid)
        return account


class GetExpense:
    def __init__(self, data):
        self.key_list = None
        self.full_list = None
        self.type = None
        self.expend = EXPENSES_OTHER
        self.income = INCOME_OTHER
        self.bill = data[9]
        self.balance = data[4]
        self.time = datetime.datetime.strptime(data[0], "%Y-%m-%d %H:%M:%S").time()

    def initialize_type(self, data):
        if self.bill == BILL_ALI:
            self.type = alipay_get_type(data)
        elif self.bill == BILL_WECHAT:
            self.type = wechatpay_get_type(data)

    def initialize_key_list(self, ownerid):
        if self.balance == "支出":
            self.key_list = Expense.objects.filter(owner_id=ownerid).values_list('key', flat=True)
        elif self.balance == "收入":
            self.key_list = Income.objects.filter(owner_id=ownerid).values_list('key', flat=True)
        elif self.balance == "/" or self.balance == "不计收支":
            self.key_list = Assets.objects.filter(owner_id=ownerid).values_list('key', flat=True)
        self.full_list = Assets.objects.filter(owner_id=ownerid).values_list('full', flat=True)

    def get_expense(self, data, ownerid):
        self.initialize_key_list(ownerid)  # 根据收支情况获取数据库中key的所有值，将其处理为列表
        self.initialize_type(data)
        actual_assets = get_default_assets(ownerid=ownerid)
        expend = self.expend
        income = self.income
        foodtime = self.time
        matching_max_order = None

        if self.balance == "支出":
            matching_keys = [k for k in self.key_list if k in data[2] or k in data[3]]  # 通过列表推导式获取所有匹配的key形成新的列表
            max_order = None
            expend_set = set()
            for matching_key in matching_keys:  # 遍历所有匹配的key，获取最大的优先级
                expense_instance = Expense.objects.filter(owner_id=ownerid, key=matching_key).first()
                if expense_instance:

                    # 通过Expenses及Payee计算优先级
                    expend_instance_priority = expense_instance.expend.count(":") * 100
                    payee_instance_priority = 50 if expense_instance.payee else 0
                    matching_max_order = expend_instance_priority + payee_instance_priority

                    # 增加早餐中餐午餐判断
                    if expense_instance.expend == "Expenses:Food" and TIME_BREAKFAST_START <= foodtime <= TIME_BREAKFAST_END:
                        expense_instance.expend += ":Breakfast"
                    elif expense_instance.expend == "Expenses:Food" and TIME_LUNCH_START <= foodtime <= TIME_LUNCH_END:
                        expense_instance.expend += ":Lunch"
                    elif expense_instance.expend == "Expenses:Food" and TIME_DINNER_START <= foodtime <= TIME_DINNER_END:
                        expense_instance.expend += ":Dinner"

                    expend_set.add(expense_instance.expend)

                if matching_max_order is not None and (
                        max_order is None or matching_max_order > max_order):  # 如果匹配到的key的matching_max_order大于max_order，则更新max_order
                    max_order = matching_max_order
                    expend = expense_instance.expend

                elif matching_max_order is not None and (
                        max_order is None or matching_max_order == max_order):  # 如果最大优先级冲突，则将Expend更新为默认Expend.
                    expend = self.expend
                    if len(expend_set) == 1:  # 如果所有关键字对应的Expend均一致，则直接调用Expend不使用默认值(Expenses:Other)
                        expend = expense_instance.expend
            return expend

        elif self.balance == "收入":
            matching_keys = [k for k in self.key_list if k in data[2] or k in data[3]]  # 通过列表推导式获取所有匹配的key形成新的列表
            for matching_key in matching_keys:
                income_instance = Income.objects.filter(owner_id=ownerid, key=matching_key).first()
                if income_instance:  # 由于作者的收入来源较少，因此暂时不考虑收入来源的优先级问题，直接返回匹配到的第一个收入来源
                    return income_instance.income
            return income

        elif self.balance == "/" or self.balance == "不计收支":
            if self.bill == BILL_ALI:
                expend = alipay_get_balance_expense(self, data, actual_assets, ownerid)
            elif self.bill == BILL_WECHAT:
                expend = wechatpay_get_balance_expense(self, data, actual_assets, ownerid)
        return expend


class GetPayee:
    def __init__(self, data):
        self.key_list = None
        self.payee = data[2]
        self.notes = data[3]
        self.bill = data[9]

    def get_payee(self, data, ownerid):
        self.key_list = list(Expense.objects.filter(owner_id=ownerid).values_list('key', flat=True))

        if data[9] == BILL_WECHAT and data[4] == "/":  # 一般微信好友转账，如妈妈->我
            return data[6][:4]
        elif data[1] == "微信红包（单发）":
            return self.payee[2:]
        elif data[1] == "转账-退款" or data[1] == "微信红包-退款":
            return "退款"
        elif '(' in self.payee and ')' in self.payee and self.notes == "Transfer":
            match = re.search(r'\((.*?)\)', self.payee)  # 提取 account 中的数字部分
            if match:
                return match.group(1)
        else:
            return self.general_payee(data, ownerid)

    def general_payee(self, data, ownerid):
        payee = self.payee
        matching_keys = [k for k in self.key_list if k in self.payee or k in self.notes]  # 通过列表推导式获取所有匹配的key形成新的列表
        max_order = None
        for matching_key in matching_keys:  # 遍历所有匹配的key，获取最大的优先级
            expense_instance = Expense.objects.filter(owner_id=ownerid, key=matching_key).first()
            if expense_instance:  # 通过Expenses及Payee计算优先级
                expend_instance_priority = expense_instance.expend.count(":") * 100
                payee_instance_priority = 50 if expense_instance.payee else 0
                matching_max_order = expend_instance_priority + payee_instance_priority

            if matching_max_order is not None and (
                    max_order is None or matching_max_order > max_order):  # 如果匹配到的key的matching_max_order大于max_order，则更新max_order
                max_order = matching_max_order

                if expense_instance is not None and expense_instance.payee is not None and expense_instance.payee != '':
                    payee = expense_instance.payee

            # 如果匹配到的key的matching_max_order等于max_order，则取原始payee。这样做的目的是为了防止多个key的matching_max_order相同，但payee不同的情况
            # 原本是想要多个payee一起展示方便选择，但是实际发现实现较复杂。如果最大优先级冲突，则将payee更新为原始payee.
            elif matching_max_order is not None and (max_order is None or matching_max_order == max_order):
                payee = self.payee

        if data[9] == BILL_ALI and payee == "":
            return data[2]
        elif data[9] == BILL_WECHAT and payee == "":
            payee = data[2]
            if payee == "/":
                return data[1]
        return payee


def calculate_commission(total, commission):
    if commission != "":
        amount = "{:.2f} CNY".format(float(total.split()[0]) - float(commission.split()[0]))
    else:
        amount = total
    return amount


def get_shouzhi(data):
    shouzhi = data[4]
    high = ""
    loss = "-"

    if shouzhi == "支出":
        return high, loss
    elif shouzhi == "收入":
        return loss, high
    elif shouzhi in ["/", "不计收支"]:
        if data[9] == BILL_ALI:
            if data[3] == "信用卡还款":
                return high, loss
            if "花呗主动还款" in data[3]:
                return high, loss
        if data[9] == BILL_WECHAT and data[1] == "信用卡还款":
            return high, loss
        return loss, high
    else:
        return None, None


def get_attribute(data, attribute_handlers):
    # 如果需要对数据进行一般性处理，也可以在这里完成

    bill_type = data[9]
    if bill_type in attribute_handlers:
        return attribute_handlers[bill_type](data)
    return None


def get_uuid(data):
    uuid_handlers = {
        BILL_ALI: alipay_get_uuid,
        BILL_WECHAT: wechatpay_get_uuid,
        BILL_CMB_CREDIT: cmb_credit_get_uuid,
        BILL_BOC_DEBIT: boc_debit_get_uuid,
        BILL_ICBC_DEBIT:icbc_debit_get_uuid,
    }
    return get_attribute(data, uuid_handlers)


def get_status(data):
    status_handlers = {
        BILL_ALI: alipay_get_status,
        BILL_WECHAT: wechatpay_get_status,
        BILL_CMB_CREDIT: cmb_credit_get_status,
        BILL_BOC_DEBIT: boc_debit_get_status,
        BILL_ICBC_DEBIT:icbc_debit_get_status,
    }
    return get_attribute(data, status_handlers)


def get_notes(data):
    notes_handlers = {
        BILL_ALI: alipay_get_notes,
        BILL_WECHAT: wechatpay_get_notes,
        BILL_CMB_CREDIT: cmb_credit_get_notes,
        BILL_BOC_DEBIT: boc_debit_get_notes,
        BILL_ICBC_DEBIT:icbc_debit_get_notes,
    }
    data[3] = data[3].replace('"', '\\"')
    return get_attribute(data, notes_handlers)


def get_amount(data):
    amount_handlers = {
        BILL_ALI: alipay_get_amount,
        BILL_WECHAT: wechatpay_get_amount,
        BILL_CMB_CREDIT: cmb_credit_get_amount,
        BILL_BOC_DEBIT: boc_debit_get_amount,
        BILL_ICBC_DEBIT: boc_debit_get_amount,
    }
    return get_attribute(data, amount_handlers)
