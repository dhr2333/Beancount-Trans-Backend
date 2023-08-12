import csv
import os
import re
import tempfile
from datetime import datetime

import chardet
from django.db.models import Max
from django.http import JsonResponse
from django.shortcuts import render

from mydemo import settings
from .models import Expense, Assets
from mydemo.utils.token import get_token_user_id

def wechat_expend(data, key_list):
    expend = ""
    type = data[1][:5]  # 获取交易类型，一共就以下四种
    if type == "零钱提现":
        expend = "Assets:Savings:Web:WechatPay"
    elif type == "零钱充值":
        for key in key_list:
            if key in data[2]:
                expend_instance = Assets.objects.get(key=key)
                expend = expend_instance.income
                return expend
            else:
                expend = "Assets:Other"
            return expend
    elif type == "零钱通转出":
        expend = "Assets:Savings:Web:WechatFund"
    elif type == "转入零钱通":
        index = data[1].find("来自")
        result = data[1][index + 2:]  # 取来自之后的所有数据，例如"建设银行(5522)"
        for key in key_list:
            if key in result:
                expend_instance = Assets.objects.get(key=key)
                expend = expend_instance.income
                return expend
            else:
                expend = "Assets:Other"
    return expend


def alipay_expend(data, key_list):
    expend = ""
    type = data[3]
    if type == "转账收款到余额宝":
        expend = "Assets:Savings:Web:AliPay"
    elif type == "余额宝-自动转入":
        expend = "Assets:Savings:Web:AliPay"
    elif type == "余额宝-转出到余额":
        expend = "Assets:Savings:Web:AliFund"
    elif type == "余额宝-单次转入":
        result = data[6]
        for key in key_list:
            if key in result:
                expend_instance = Assets.objects.get(key=key)
                expend = expend_instance.income
                return expend
            else:
                expend = "Assets:Other"
    elif type == "余额宝-转出到银行卡":
        expend = "Assets:Savings:Web:AliFund"
    elif type == "充值-普通充值":
        expend = "Assets:Other"  # 支付宝账单中银行卡充值到余额时没有任何银行的信息，需要手动对账
    elif type == "提现-实时提现":
        expend = "Assets:Savings:Web:AliPay"
    else:
        expend = "Assets:Other"
    return expend


def get_expend(data,ownerid):
    expend = ""
    # 获取数据库中key的所有值，将其处理为列表
    if data[4] == "支出":  # 收/支栏 值为"收入"或"支出"
        # TODO
        key_list = Expense.objects.filter(owner_id=ownerid).values_list('key', flat=True)
        print(key_list)
        # for循环获取所有值，并与payee进行比对
        for key in key_list:
            if key in data[2] or key in data[3]:
                expend_instance = Expense.objects.get(key=key)
                expend = expend_instance.expend
                return expend
        if expend == "":
            expend = "Expenses:Other"
    elif data[4] == "收入":
        expend = "Income:Other"
    elif data[4] == "/" or data[4] == "不计收支":  # 收/支栏 值为/
        key_list = Assets.objects.values_list('key', flat=True)
        if data[9] == "wechat":
            expend = wechat_expend(data, key_list)
        elif data[9] == "alipay":
            expend = alipay_expend(data, key_list)
    return expend


def wechat_account(data, key_list):
    account = ""
    type = data[1][:5]
    if type == "零钱提现":
        for key in key_list:
            if key in data[2]:
                account_instance = Assets.objects.get(key=key)
                account = account_instance.income
                return account
        account = "Assets:Other"
    elif type == "零钱充值":
        account = "Assets:Savings:Web:WechatPay"
    elif type == "零钱通转出":
        index = data[1].find("到")
        result = data[1][index + 1:]  # 取来自之后的所有数据，例如"建设银行(5522)"
        for key in key_list:
            if key in result:
                account_instance = Assets.objects.get(key=key)
                account = account_instance.income
                return account
            else:
                account = "Assets:Other"
            return account
    elif type == "转入零钱通":
        account = "Assets:Savings:Web:WechatFund"
    return account


def alipay_account(data, key_list):
    account = ""
    type = data[3]
    if type == "转账收款到余额宝":
        account = "Assets:Savings:Web:AliFund"
    elif type == "余额宝-自动转入":
        account = "Assets:Savings:Web:AliFund"
    elif type == "余额宝-转出到余额":
        account = "Assets:Savings:Web:AliPay"
    elif type == "余额宝-单次转入":
        account = "Assets:Savings:Web:AliFund"
    elif type == "余额宝-转出到银行卡":
        result = data[6]
        for key in key_list:
            if key in result:
                account_instance = Assets.objects.get(key=key)
                account = account_instance.income
                return account
            else:
                account = "Assets:Other"
    elif type == "充值-普通充值":
        account = "Assets:Savings:Web:AliPay"  # 支付宝账单中银行卡充值到余额时没有任何银行的信息，需要手动对账
    elif type == "提现-实时提现":
        account = "Assets:Other"  # 支付宝账单中提现最大颗粒度只到具体银行，若该银行有两张银行卡便有问题，需要手动对账
    else:
        account = "Assets:Other"
    return account


def get_account(data,ownerid):
    account = ""
    key = data[6]
    if "&" in key:  # 该判断用于解决支付宝中"&[红包]"导致无法被匹配的问题
        sub_strings = key.split("&")
        key = sub_strings[0]
    key_list = Assets.objects.filter(owner_id=ownerid).values_list('key', flat=True)
    print(key_list)
    if data[4] == "收入" or data[4] == "支出":  # 收/支栏 值为"收入"或"支出"
        if key in key_list:
            account_instance = Assets.objects.get(key=key)
            account = account_instance.income
            return account
        elif key == "" and data[9] == "alipay":  # 第三方平台到支付宝的收入
            account = "Assets:Savings:Web:AliPay"
        else:
            if '(' in key and ')' in key:
                digits = key.split('(')[1].split(')')[0]  # 提取 account 中的数字部分
                # 判断提取到的数字是否在列表中
                if digits in key_list:
                    account_instance = Assets.objects.get(key=digits)
                    account = account_instance.income
                    return account
                else:
                    return "Assets:Other"
    elif data[4] == "/" or data[4] == "不计收支":  # 收/支栏 值为/
        if data[9] == "wechat":
            account = wechat_account(data, key_list)
        elif data[9] == "alipay":
            account = alipay_account(data, key_list)
    return account


def get_payee(data):
    # 初始数值为data[2]
    # 获取数据库中数据与object和commodity进行对比
    # 如果数据库中数据在object或comdodity中，获取数据库中的payee
    #    如果数据库中的payee为空
    #      微信则获取data[1]
    #      支付宝则获取data[2]
    # 如果数据库中数据不在object或comdodity中（例如"/"或者小商家）
    #    如果是小商家，获取data[2]即可
    #    如果是"/"，获取data[1]
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
    notes = data[3]
    if data[4] == "/":
        notes = data[1]
    return notes


def get_shouzhi(shouzhi):
    expend_fuhao = ""
    account_fuhao = ""
    if shouzhi == "收入":
        expend_fuhao = "-"
        account_fuhao = "+"
    elif shouzhi == "支出":
        expend_fuhao = "+"
        account_fuhao = "-"
    elif shouzhi == "/" or shouzhi == "不计收支":
        expend_fuhao = "-"
        account_fuhao = "+"
    return expend_fuhao, account_fuhao


def get_money(data):
    try:
        money = "{:.2f} CNY".format(float(data[5]))  # 支付宝账单格式为"10.00"，直接以数字形式返回即可
    except ValueError:
        money = "{:.2f} CNY".format(float(data[5][1:]))  # 微信账单格式为"￥10.00"，需要转换
    return money


def format(data,owner_id):
    """
        date : 时间       2023-04-28
        money : 金额      23.00 CNY
        payee : 收款方    浙江古茗
        notes : 备注      商品详情
        expend : 支付方式  Expenses:Food:DrinkFruit
        account : 账户    Liabilities:CreditCard:Bank:ZhongXin:C6428
    """
    date = datetime.strptime(data[0], "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d")
    time = datetime.strptime(data[0], "%Y-%m-%d %H:%M:%S").strftime("%H:%M:%S")
    money = get_money(data)
    payee = get_payee(data)
    notes = get_notes(data)
    expend_fuhao, account_fuhao = get_shouzhi(data[4])
    expend = get_expend(data,owner_id)
    account = get_account(data,owner_id)
    commission = data[8][4:]
    if data[4] == "/":
        if commission != "":
            new_money = "{:.2f} CNY".format(float(float(money.split()[0]) - float(commission.split()[0])))
            return {"date": date, "time": time, "payee": payee, "notes": notes, "expend": expend,
                    "expend_fuhao": expend_fuhao,
                    "account": account, "account_fuhao": account_fuhao, "money": money, "new_money": new_money}
        return {"date": date, "time": time, "payee": payee, "notes": notes, "expend": expend,
                "expend_fuhao": expend_fuhao,
                "account": account, "account_fuhao": account_fuhao, "money": money}
    return {"date": date, "time": time, "payee": payee, "notes": notes, "expend": expend, "expend_fuhao": expend_fuhao,
            "account": account, "account_fuhao": account_fuhao, "money": money}


def beancount_outfile(data,owner_id):
    """
        格式化，输出格式

        2023-04-29 * "浙江古茗" "商品详情"
        Expenses:Food:DrinkFruit 43.50 CNY
        Liabilities:CreditCard:Bank:ZhongXin:C6428 -43.50 CNY
    """
    # [time, type, object, commodity, balance, amount, way, status, notes, bill]
    shiji_list = []
    for row in data:
        if row[7] == "交易成功":
            if row[2] == "兴全基金管理有限公司" or row[6] == "亲情卡(凯义(王凯义))":  # 忽略余额宝收益，最后做balance结余断言时统一归于基金收益
                continue
            entry = format(row,owner_id)
            shiji = "{0} * \"{1}\" \"{2}\"\n    time: \"{3}\"\n    {4} {5}{6}\n    {7} {8}{9}\n\n".format(
                entry["date"], entry["payee"], entry["notes"], entry["time"], entry["expend"], entry["expend_fuhao"],
                entry["money"],
                entry["account"], entry["account_fuhao"], entry["money"])
            if entry["notes"] == "零钱提现":
                shiji = "{0} * \"{1}\" \"{2}\"\n    time: \"{3}\"\n    {4} {5}{6} \n    {7} {8}{9}\n    {10}\n\n".format(
                    entry["date"], entry["payee"], entry["notes"], entry["time"], entry["expend"],
                    entry["expend_fuhao"],
                    entry["money"],
                    entry["account"], entry["account_fuhao"], entry["new_money"], "Expenses:Finance:Commission")
            elif entry == {}:
                continue
            mouth = shiji[5:7]
            year = shiji[0:4]
            # os.path.dirname(settings.BASE_DIR) 获取当前文件所在的Django项目的根目录的父目录（将解析后的数据存放于该项目的同级目录Assets）
            # print(os.path.dirname(settings.BASE_DIR) + "/Assets" + "/" + year + "/" + mouth + "-expenses.bean")
            file = os.path.dirname(
                settings.BASE_DIR) + "/Beancount-Trans-Assets" + "/" + year + "/" + mouth + "-expenses.bean"
            createdir(file)
            shiji_list.append(shiji)
            with open(file, mode='a') as file:
                file.write(shiji)
        else:
            continue
    return shiji_list


def createdir(file_path):
    file_list = [
        "00.bean",
        "01-expenses.bean",
        "02-expenses.bean",
        "03-expenses.bean",
        "04-expenses.bean",
        "05-expenses.bean",
        "06-expenses.bean",
        "07-expenses.bean",
        "08-expenses.bean",
        "09-expenses.bean",
        "10-expenses.bean",
        "11-expenses.bean",
        "12-expenses.bean",
        "cycle.bean",
        "event.bean",
        "income.bean",
        "invoice.bean",
        "price.bean",
        "time.bean"
    ]
    insert_contents = '''include "01-expenses.bean"
include "02-expenses.bean"
include "03-expenses.bean"
include "04-expenses.bean"
include "05-expenses.bean"
include "06-expenses.bean"
include "07-expenses.bean"
include "09-expenses.bean"
include "10-expenses.bean"
include "11-expenses.bean"
include "12-expenses.bean"
include "cycle.bean"
include "event.bean"
include "income.bean"
include "invoice.bean"
include "price.bean"
include "time.bean"'''
    dir_path = os.path.split(file_path)[0]  # 获取账单的绝对路径，例如 */Beancount-Trans/Beancount-Trans-Assets/2023
    dir_name = os.path.basename(dir_path)
    if not os.path.isdir(dir_path):  # 判断年份账单是否存在，若不存在则创建目录并在main.bean中include该目录
        os.makedirs(dir_path)
        insert_include = f'\ninclude "{dir_name}/00.bean"'
        main_file = os.path.dirname(dir_path) + "/main.bean"
        with open(main_file, 'a') as main:
            main.write(insert_include)
        for file_name in file_list:  # 该for循环用于创建按年划分的所有文件
            createfile = os.path.join(dir_path, file_name)
            open(createfile, 'w').close()
            if file_name == "00.bean":  # 00.bean文件会include其他文件来让beancount正确识别
                with open(createfile, 'w') as f:
                    f.write(insert_contents)


# 支付宝
def alipay(reader):
    row = 0
    while row < 24:
        next(reader)
        row += 1
    list = []
    try:
        for row in reader:
            # 提取需要的字段
            time = row[0]  # 交易时间
            type = row[1]  # 交易类型
            object = row[2]  # 交易对方
            commodity = row[4]  # 商品
            balance = "/" if row[5] == "不计收支" else row[5]  # 收支
            amount = row[6]  # 金额
            way = "余额" if row[7] == '                    ' else row[7]  # 支付方式
            status = row[8]  # 交易状态
            notes = "/" if row[11] == '                    ' else row[11]  # 备注
            bill = "alipay"
            single_list = [time, type, object, commodity, balance, amount, way, status, notes, bill]
            new_list = []
            for item in single_list:
                new_item = item.strip()
                new_list.append(new_item)
            list.append(new_list)
    except UnicodeDecodeError:
        print(row)
    return list


# 微信
def wechatpay(reader):  # 返回的列表具体的值注释在该函数
    row = 0
    while row < 16:
        next(reader)
        row += 1
    list = []
    for row in reader:
        time = row[0]  # 交易时间(2023-03-03 09:03:00)
        type = row[1]  # 交易类型（微信通过该字段判断各账户间转账，支付宝通过该字段判断分类(但分类并不准，推荐忽略)）
        object = row[2]  # 交易对方
        commodity = row[3]  # 商品（支付宝通过该字段判断各账户间转账）
        balance = row[4]  # 收支(收入/支出/不计收支)
        amount = row[5]  # 金额(￥10.00/10.00)
        way = row[6]  # 支付方式
        status = "交易成功"  # 交易状态(支付宝账单中存在很多其他状态，但处理的时候只会处理"交易成功"的数据，其他数据丢弃)
        notes = row[10]  # 备注(微信账单中该列为手续费，支付宝账单中全为空)
        bill = "wechat"  # 账单(用于区分传入的各个账单以调用不同的函数处理)
        single_list = [time, type, object, commodity, balance, amount, way, status, notes, bill]
        list.append(single_list)
    return list


def analyze(request):
    """ 解析，上传文件后提取需要的字段 """
    if request.method == "POST":
        owner_id = get_token_user_id(request)  # 根据前端传入的JWT Token获取owner_id,如果是非认证用户或者Token过期则返回1(默认用户)
        uploaded_file = request.FILES.get('trans', None)
        content = uploaded_file.read()
        encoding = chardet.detect(content)['encoding']
        # 创建临时文件并将内容写入临时文件
        temp = tempfile.NamedTemporaryFile(delete=False)
        temp.write(content)
        temp.flush()
        # 打开微信账单文件
        with open(temp.name, newline='', encoding=encoding, errors="ignore") as csvfile:
            # 读取CSV文件
            reader = csv.reader(csvfile)
            one = next(reader)[0]
            # 跳过表头
            if one == "微信支付账单明细":
                list = wechatpay(reader)
            elif one == "------------------------------------------------------------------------------------":
                list = alipay(reader)
        # 删除临时文件
        format_list = beancount_outfile(list,owner_id)
        # json_list = json.dumps(format_list)
        os.unlink(temp.name)

        # return HttpResponse(json_list, content_type='application/json')
        return JsonResponse(format_list, safe=False, content_type='application/json')
    title = "trans"
    context = {"title": title}
    return render(request, "translate/trans.html", context)
