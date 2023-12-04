import re

# from translate.views.view import ALIPAY,ALIFUND,HUABEI
from translate.models import Assets
from translate.utils import ASSETS_OTHER
from translate.utils import PaymentStrategy
from translate.utils import pattern

BILL_ALI = "alipay"


class AliPayStrategy(PaymentStrategy):
    def get_data(self, bill):
        # 实现获取支付宝支付数据的逻辑
        row = 0
        while row < 24:
            next(bill)
            row += 1
        list = []
        try:
            for row in bill:
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
                uuid = row[9]
                single_list = [time, type, object, commodity, balance, amount, way, status, notes, bill, uuid]
                new_list = []
                for item in single_list:
                    new_item = item.strip()
                    new_list.append(new_item)
                list.append(new_list)
        except UnicodeDecodeError:
            print("error row = ", row)
        return list


def alipay_get_expense_account(self, assets, ownerid):
    key = self.key
    if key in self.key_list:
        account_instance = Assets.objects.filter(key=key, owner_id=ownerid).first()
        return account_instance.assets
    elif key == "":
        return assets["ALIPAY"]
    elif '(' in key and ')' in key:
        digits = key.split('(')[1].split(')')[0]  # 提取 account 中的数字部分，例如中信银行信用卡(6428) -> 6428
        if digits in self.key_list:  # 判断提取到的数字是否在列表中
            account_instance = Assets.objects.filter(key=digits, owner_id=ownerid).first()
            return account_instance.assets
        else:
            return ASSETS_OTHER  # 提取到的数字不在列表中，说明该账户不在数据库中，需要手动对账


def alipay_get_income_account(self, assets, ownerid):
    key = self.key
    if key in self.key_list:
        account_instance = Assets.objects.filter(key=key, owner_id=ownerid).first()
        return account_instance.assets
    elif key == "":
        return assets["ALIPAY"]
    elif '(' in key and ')' in key:
        digits = key.split('(')[1].split(')')[0]  # 提取 account 中的数字部分，例如中信银行信用卡(6428) -> 6428
        if digits in self.key_list:  # 判断提取到的数字是否在列表中
            account_instance = Assets.objects.filter(key=digits, owner_id=ownerid).first()
            return account_instance.assets
        else:
            return ASSETS_OTHER  # 提取到的数字不在列表中，说明该账户不在数据库中，需要手动对账


def alipay_get_balance_account(self, data, assets, ownerid):
    account = "Unknown-Account"
    if self.type == "转账收款到余额宝":
        account = assets["ALIFUND"]
    elif self.type == "余额宝-自动转入":
        account = assets["ALIFUND"]
    elif self.type == "余额宝-转出到余额":
        account = assets["ALIPAY"]
    elif self.type == "余额宝-单次转入":
        account = assets["ALIFUND"]
    elif self.type == "余额宝-转出到银行卡":
        result = data[6]
        for key in self.key_list:
            if key in result:
                account_instance = Assets.objects.filter(key=key, owner_id=ownerid).first()
                account = account_instance.assets
                return account
        account = ASSETS_OTHER
    elif self.type == "充值-普通充值":
        account = assets["ALIPAY"]  # 支付宝账单中银行卡充值到余额时没有任何银行的信息，需要手动对账
    elif self.type == "提现-实时提现":  # 利用账单中的"交易对方"与数据库中的"full"进行对比，若被包含可直接匹配assets
        result = data[2] + "储蓄卡"  # 例如"宁波银行储蓄卡"
        for full in self.full_list:
            if result in full:
                account_instance = Assets.objects.filter(full=full, owner_id=ownerid).first()
                account = account_instance.assets
                return account
    elif self.type == "信用卡还款" or re.match(pattern["花呗"], self.type):
        result = data[6]
        for key in self.key_list:
            if key in result:
                account_instance = Assets.objects.filter(key=key, owner_id=ownerid).first()
                account = account_instance.assets
                return account
            else:
                account = ASSETS_OTHER
    elif re.match(pattern["基金"], self.type):
        result = data[3][data[3].index("卖出至") + len("卖出至"):]
        for key in self.key_list:
            if result in key:
                account_instance = Assets.objects.filter(key=key, owner_id=ownerid).first()
                account = account_instance.assets
                return account
        account = ASSETS_OTHER
    else:
        account = ASSETS_OTHER  # 支付宝账单中提现最大颗粒度只到具体银行，若该银行有两张银行卡便有问题，需要手动对账
    return account


def alipay_get_balance_expense(self, data, assets, ownerid):
    expend = "Unknown-Expend"
    if self.type == "转账收款到余额宝":
        expend = assets["ALIPAY"]
    elif self.type == "余额宝-自动转入":
        expend = assets["ALIPAY"]
    elif self.type == "余额宝-转出到余额":
        expend = assets["ALIFUND"]
    elif self.type == "余额宝-单次转入":
        result = data[6]
        for key in self.key_list:
            if key in result:
                # expend_instance = Assets.objects.get(key=key)
                expend_instance = Assets.objects.filter(key=key, owner_id=ownerid).first()
                expend = expend_instance.assets
                return expend
            else:
                expend = ASSETS_OTHER
    elif self.type == "余额宝-转出到银行卡":
        expend = assets["ALIFUND"]
    elif self.type == "充值-普通充值":
        expend = ASSETS_OTHER  # 支付宝账单中银行卡充值到余额时没有任何银行的信息，需要手动对账
    elif self.type == "提现-实时提现":
        expend = assets["ALIPAY"]
    elif re.match(pattern["花呗"], self.type):  # 账单类型匹配"花呗主动还款-2022年09月账单"
        expend = assets["HUABEI"]
    elif self.type == "信用卡还款":
        result = data[2] + "信用卡"  # 例如"华夏银行信用卡"
        for full in self.full_list:
            if result in full:
                expend_instance = Assets.objects.filter(full=full, owner_id=ownerid).first()
                expend = expend_instance.assets
                return expend
    else:
        expend = ASSETS_OTHER
    return expend


def alipay_get_type(data):
    return data[3]


def alipay_initalize_key(data):
    key = data[6]
    if "&" in key:  # 用于解决支付宝中"&[红包]"导致无法被匹配的问题
        sub_strings = key.split("&")
        key = sub_strings[0]
    return key


def alipay_get_uuid(data):
    return data[10]


def alipay_get_status(data):
    return "ALiPay - " + data[7]


def alipay_get_amount(data):
    return "{:.2f} CNY".format(float(data[5]))  # 支付宝账单格式为"10.00"，直接以数字形式返回即可


def alipay_get_notes(data):
    if data[3] == "Transfer":
        return "无备注转账"
    elif data[3] == "发普通红包":
        return "发普通红包"
    elif data[3] == "收到普通红包":
        return "收到普通红包"
    return data[3]

# def alipay_get_payee(self):
#     if '(' in self.payee and ')' in self.payee and self.notes == "Transfer":
#         match = re.search(r'\((.*?)\)', self.payee)  # 提取 account 中的数字部分
#         if match:
#             return match.group(1)
