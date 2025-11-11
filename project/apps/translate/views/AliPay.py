# project/apps/translate/views/AliPay.py
import re
# import logging

from project.apps.maps.models import Assets
from project.apps.translate.utils import ASSETS_OTHER, OPENBALANCE, pattern
from project.apps.translate.services.mapping_provider import extract_account_string

# alipay_csvfile_identifier = "------------------------------------------------------------------------------------"

# class AliPayInitStrategy(InitStrategy):
#     def init(self, bill, **kwargs):
#         import itertools
#         bill = itertools.islice(bill, 24, None)  # 跳过前24行
#         records = []

#         try:
#             for row in bill:
#                 transaction_type = "/" if row[5] == "不计收支" else row[5]
#                 payment_method = "余额" if row[7].strip() == '' else row[7].strip()
#                 notes = "/" if row[11].strip() == '' else row[11].strip()

#                 record = {
#                     'transaction_time': row[0].strip(),  # 交易时间
#                     'transaction_category': row[1].strip(),  # 交易类型
#                     'counterparty': row[2].strip(),  # 交易对方
#                     'commodity': row[4].strip(),  # 商品
#                     'transaction_type': transaction_type.strip(),  # 收支类型（收入/支出/不计收支）
#                     'amount': row[6].strip(),  # 金额
#                     'payment_method': payment_method.split('&')[0],  # 支付方式
#                     'transaction_status': row[8].strip(),  # 交易状态
#                     'notes': notes,  # 备注
#                     'bill_identifier': BILL_ALI,  # 账单类型
#                     'uuid': row[9].strip(),  # 交易单号
#                     'discount': True if "&" in payment_method else False  # 支付方式
#                 }
#                 records.append(record)

#         except UnicodeDecodeError as e:
#             logging.error(f"Unicode decode error at row={row}: {str(e)}")
#         except Exception as e:
#             logging.error(f"Unexpected error: {str(e)}")

#         return records


# def alipay_ignore(self, data):
#     if data['bill_identifier'] == BILL_ALI and data['transaction_status'] in ["退款成功", "交易关闭", "解冻成功", "信用服务使用成功", "已关闭", "还款失败", "等待付款", "芝麻免押下单成功"]:
#         return True
#     elif data['bill_identifier'] == BILL_ALI and  re.match(pattern["余额宝"], data['commodity']):
#         return True
#     else:
#         return False

# def alipay_fund_ignore(self, data):
#     if data['bill_identifier'] == BILL_ALI:
#         return data['transaction_category'] in ["转账收款到余额宝", "余额宝-自动转入", "余额宝-单次转入"]


def alipay_get_expense_account(self, assets, ownerid):
    key = self.key
    if key in self.key_list:
        account_instance = self.find_asset_by_key(key)
        if account_instance and account_instance.assets:
            return extract_account_string(account_instance.assets)
        return ASSETS_OTHER
    elif key == "":
        return assets["ALIPAY"]
    elif '(' in key and ')' in key:
        digits = key.split('(')[1].split(')')[0]  # 提取 account 中的数字部分，例如中信银行信用卡(6428) -> 6428
        if digits in self.key_list:  # 判断提取到的数字是否在列表中
            account_instance = self.find_asset_by_key(digits)
            if account_instance and account_instance.assets:
                return extract_account_string(account_instance.assets)
            return ASSETS_OTHER
        else:
            return ASSETS_OTHER  # 提取到的数字不在列表中，说明该账户不在数据库中，需要手动对账
    else:
        return ASSETS_OTHER


def alipay_get_income_account(self, assets, ownerid):
    key = self.key
    if key in self.key_list:
        account_instance = self.find_asset_by_key(key)
        if account_instance and account_instance.assets:
            return extract_account_string(account_instance.assets)
        return ASSETS_OTHER
    elif key == "":
        return assets["ALIPAY"]
    elif '(' in key and ')' in key:
        digits = key.split('(')[1].split(')')[0]  # 提取 account 中的数字部分，例如中信银行信用卡(6428) -> 6428
        if digits in self.key_list:  # 判断提取到的数字是否在列表中
            account_instance = self.find_asset_by_key(digits)
            if account_instance and account_instance.assets:
                return extract_account_string(account_instance.assets)
            return ASSETS_OTHER
        else:
            return ASSETS_OTHER  # 提取到的数字不在列表中，说明该账户不在数据库中，需要手动对账


def alipay_get_balance_account(self, data, assets, ownerid):
    # account = "Unknown-Account"  # 方便排查问题
    account = self.account
    if self.type == "转账收款到余额宝":
        account = assets["ALIPAY"]
    elif self.type == "余额宝-自动转入":
        account = assets["ALIPAY"]
    elif self.type == "余额宝-转出到余额":
        account = assets["ALIFUND"]
    elif self.type == "余额宝-单次转入":
        result = data['payment_method']
        for key in self.key_list:
            if key in result:
                expend_instance = self.find_asset_by_key(key)
                if expend_instance and expend_instance.assets:
                    return extract_account_string(expend_instance.assets)
                return ASSETS_OTHER
            else:
                account = ASSETS_OTHER
    elif self.type == "余额宝-转出到银行卡":
        account = assets["ALIFUND"]
    elif self.type == "充值-普通充值":
        account = ASSETS_OTHER  # 支付宝账单中银行卡充值到余额时没有任何银行的信息，需要手动对账
    elif self.type == "提现-实时提现" or self.type == "提现-快速提现":  # 利用账单中的"交易对方"与数据库中的"full"进行对比，若被包含可直接匹配assets
        account = assets["ALIPAY"]
    elif "亲情卡" in data['payment_method']:
        account = OPENBALANCE
    else:
        result = data['payment_method']
        for key in self.key_list:
            if key in result:
                account_instance = self.find_asset_by_key(key)
                if account_instance and account_instance.assets:
                    return extract_account_string(account_instance.assets)
                return ASSETS_OTHER
            else:
                account = ASSETS_OTHER
        # account = ASSETS_OTHER  # 支付宝账单中提现最大颗粒度只到具体银行，若该银行有两张银行卡便有问题，需要手动对账
    return account


def alipay_get_balance_expense(self, data, assets, ownerid):
    # expend = "Unknown-Expend"  # 方便排查问题
    expend = self.expend
    if self.type == "转账收款到余额宝":
        expend = assets["ALIFUND"]
    elif self.type == "余额宝-自动转入":
        expend = assets["ALIFUND"]
    elif self.type == "余额宝-转出到余额":
        expend = assets["ALIPAY"]
    elif self.type == "余额宝-单次转入":
        expend = assets["ALIFUND"]
    elif self.type == "余额宝-转出到银行卡":
        result = data['payment_method']
        for key in self.key_list:
            if key in result:
                expend_instance = self.find_asset_by_key(key)
                if expend_instance and expend_instance.assets:
                    return extract_account_string(expend_instance.assets)
                return ASSETS_OTHER
        expend = ASSETS_OTHER
    elif self.type == "充值-普通充值":
        expend = assets["ALIPAY"]  # 支付宝账单中银行卡充值到余额时没有任何银行的信息，需要手动对账
    elif self.type == "提现-实时提现" or self.type == "提现-快速提现":
        result = data['counterparty'] + "储蓄卡"  # 例如"宁波银行储蓄卡"
        for full in self.full_list:
            if result in full:
                expend_instance = self.find_asset_by_full(full)
                if expend_instance and expend_instance.assets:
                    return extract_account_string(expend_instance.assets)
                return ASSETS_OTHER
    elif re.match(pattern["花呗主动还款"], self.type) or re.match(pattern["花呗自动还款"], self.type):  # 账单类型匹配"花呗主动还款-2022年09月账单"
        expend = assets["HUABEI"]
    elif ("蚂蚁借呗放款至银行卡" in self.type) or ("蚂蚁借呗还款" in self.type):
        expend = assets["JIEBEI"]
    elif ("备用金取出至余额" in self.type) or ("备用金归还" in self.type):
        expend = assets["BEIYONGJIN"]
    elif self.type == "信用卡还款":
        result = data['counterparty'] + "信用卡"  # 例如"招商银行信用卡"
        for full in self.full_list:
            if result in full:
                expend_instance = self.find_asset_by_full(full)
                if expend_instance and expend_instance.assets:
                    return extract_account_string(expend_instance.assets)
                return ASSETS_OTHER
    elif re.match(pattern["基金"], self.type):
        result = data['commodity'][data['commodity'].index("卖出至") + len("卖出至"):]
        for key in self.key_list:
            if result in key:
                expend_instance = self.find_asset_by_key(key)
                if expend_instance and expend_instance.assets:
                    return extract_account_string(expend_instance.assets)
                return ASSETS_OTHER
        expend = ASSETS_OTHER
    else:
        expend = ASSETS_OTHER
    return expend


def alipay_get_type(data):
    return data['commodity']


def alipay_initalize_key(data):
    key = data['payment_method']
    if "&" in key:  # 用于解决支付宝中"&[红包]"导致无法被匹配的问题
        sub_strings = key.split("&")
        key = sub_strings[0]
    return key


def alipay_get_uuid(data):
    return data['uuid']


def alipay_get_status(data):
    return "ALiPay - " + data['transaction_status']


def alipay_get_amount(data):
    return "{:.2f}".format(float(data['amount']))  # 支付宝账单格式为"10.00"，直接以数字形式返回即可


def alipay_get_note(data):
    if data['commodity'] == "Transfer":
        return "Transfer(无备注转账)"
    elif data['commodity'] == "发普通红包":
        return "发普通红包"
    elif data['commodity'] == "收到普通红包":
        return "收到普通红包"
    return data['commodity']


def alipay_get_tag(data):
    pass


def alipay_get_commission(data):
    return data['notes'][4:]


def alipay_installment_granularity(data):
    return "MONTHLY"  # 默认以月进行支付 #TODO


def alipay_installment_cycle(data):
    return 3  #TODO ，硬编码，需修改


def alipay_get_discount(data):
    return data['discount']


# IgnoreData.alipay_ignore = alipay_ignore
# IgnoreData.alipay_fund_ignore = alipay_fund_ignore