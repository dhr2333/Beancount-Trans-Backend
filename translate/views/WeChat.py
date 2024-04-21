import logging

# from translate.views.view import WECHATPAY, WECHATFUND
from translate.models import Assets
from translate.utils import ASSETS_OTHER, PaymentStrategy, BILL_WECHAT


class WeChatPayStrategy(PaymentStrategy):
    def get_data(self, bill):
        # 实现获取微信支付数据的逻辑
        row = 0
        while row < 16:
            next(bill)
            row += 1
        list = []
        try:
            for row in bill:
                time = row[0]  # 交易时间(2023-03-03 09:03:00)
                type = row[1]  # 交易类型（微信通过该字段判断各账户间转账，支付宝通过该字段判断分类(但分类并不准，推荐忽略)）
                object = row[2]  # 交易对方
                commodity = row[3]  # 商品（支付宝通过该字段判断各账户间转账）
                balance = row[4]  # 收支(收入/支出/不计收支)
                amount = row[5]  # 金额(￥10.00/10.00)
                way = row[6]  # 支付方式
                status = row[7]  # 交易状态(支付宝账单中存在很多其他状态，但处理的时候只会处理"交易成功"的数据，其他数据丢弃)
                notes = row[10]  # 备注(微信账单中该列为手续费，支付宝账单中全为空)
                bill = BILL_WECHAT  # 账单(用于区分传入的各个账单以调用不同的函数处理)
                uuid = row[8]  # 交易单号
                single_list = [time, type, object, commodity, balance, amount, way, status, notes, bill, uuid]
                list.append(single_list)
        except UnicodeDecodeError:
            logging.error("error row = ", row)
        return list


def wechatpay_get_expense_account(self, assets, ownerid):
    key = self.key
    if key in self.key_list:
        account_instance = Assets.objects.filter(key=key, owner_id=ownerid).first()
        return account_instance.assets
    elif '(' in key and ')' in key:
        digits = key.split('(')[1].split(')')[0]  # 提取 account 中的数字部分，例如中信银行信用卡(6428) -> 6428
        if digits in self.key_list:  # 判断提取到的数字是否在列表中
            account_instance = Assets.objects.filter(key=digits, owner_id=ownerid).first()
            return account_instance.assets
        else:
            return ASSETS_OTHER  # 提取到的数字不在列表中，说明该账户不在数据库中，需要手动对账


def wechatpay_get_income_account(self, assets, ownerid):
    key = self.key
    if key in self.key_list:
        account_instance = Assets.objects.filter(key=key, owner_id=ownerid).first()
        return account_instance.assets


def wechatpay_get_balance_account(self, data, assets, ownerid):
    account = "Unknown-Account"
    if self.type == "零钱提现":
        for key in self.key_list:
            if key in data[2]:
                account_instance = Assets.objects.filter(key=key, owner_id=ownerid).first()
                account = account_instance.assets
                return account
        account = ASSETS_OTHER
    elif self.type == "零钱充值":
        account = assets["WECHATPAY"]
    elif self.type == "零钱通转出":
        index = data[1].find("到")
        result = data[1][index + 1:]  # 取来自之后的所有数据，例如"建设银行(5522)"
        for key in self.key_list:
            if key in result:
                account_instance = Assets.objects.filter(key=key, owner_id=ownerid).first()
                account = account_instance.assets
                return account
        account = ASSETS_OTHER
    elif self.type == "转入零钱通":
        account = assets["WECHATFUND"]
    elif self.type == "信用卡还款":
        result = data[6]
        for key in self.key_list:
            if key in result:
                account_instance = Assets.objects.filter(key=key, owner_id=ownerid).first()
                account = account_instance.assets
                return account
            else:
                account = ASSETS_OTHER
    elif self.type == "购买理财通":
        result = data[6] + "储蓄卡"  # 目前无法区分同一家银行的多张储蓄卡
        for full in self.full_list:
            if result in full:
                account_instance = Assets.objects.filter(full=full, owner_id=ownerid).first()
                account = account_instance.assets
                return account
    return account


def wechatpay_get_balance_expense(self, data, assets, ownerid):
    expend = "Unknown-Expend"
    if self.type == "零钱提现":
        expend = assets["WECHATPAY"]
    elif self.type == "零钱充值":
        for key in self.key_list:
            if key in data[2]:
                # expend_instance = Assets.objects.get(key=key)
                expend_instance = Assets.objects.filter(key=key, owner_id=ownerid).first()
                expend = expend_instance.assets
                return expend
        expend = ASSETS_OTHER
    elif self.type == "零钱通转出":
        expend = assets["WECHATFUND"]
    elif self.type == "转入零钱通":
        index = data[1].find("来自")
        result = data[1][index + 2:]  # 取来自之后的所有数据，例如"建设银行(5522)"
        for key in self.key_list:
            if key in result:
                # expend_instance = Assets.objects.get(key=key)
                expend_instance = Assets.objects.filter(key=key, owner_id=ownerid).first()
                expend = expend_instance.assets
                return expend
        expend = ASSETS_OTHER
    elif self.type == "信用卡还款":
        result = data[2][:data[2].index("还款")]  # 例如"华夏银行信用卡"
        for full in self.full_list:
            if result in full:
                account_instance = Assets.objects.filter(full=full, owner_id=ownerid).first()
                account = account_instance.assets
                return account
    elif self.type == "购买理财通":
        expend = ASSETS_OTHER
    return expend


def wechatpay_get_type(data):
    return data[1][:5]


def wechatpay_initalize_key(self, data):
    return data[6]


def wechatpay_get_uuid(data):
    return data[10].rstrip("\t")


def wechatpay_get_status(data):
    return "WeChat - " + data[7]


def wechatpay_get_amount(data):
    return "{:.2f} CNY".format(float(data[5][1:]))  # 微信账单格式为"￥10.00"，需要转换


def wechatpay_get_notes(data):
    if data[4] == "/":  # 收支为/时，备注为交易类型
        return data[1]
    return data[3]

# def wechatpay_get_payee(self, data):
#     if data[4] == "/":
#         return data[6][:4]
#     elif data[1] == "微信红包（单发）":
#         return self.payee[2:]
#     elif data[1] == "转账-退款" or data[1] == "微信红包-退款":
#         return "退款"
