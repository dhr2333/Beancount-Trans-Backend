import logging
import re

from translate.models import Assets
from translate.utils import InitStrategy, IgnoreData, ASSETS_OTHER, BILL_WECHAT

wechat_csvfile_identifier = "微信支付账单明细"


class WeChatInitStrategy(InitStrategy):
    def init(self, bill, **kwargs):
        import itertools
        bill = itertools.islice(bill, 16, None)
        records = []
        try:
            for row in bill:
                record = {
                    'transaction_time': row[0],  # 交易时间
                    'transaction_category': row[1],  # 交易类型
                    'counterparty': row[2],  # 交易对方
                    'commodity': row[3],  # 商品
                    'transaction_type': row[4],  # 收支类型（收入/支出/不计收支）
                    'amount': row[5],  # 金额
                    'payment_method': row[6],  # 支付方式
                    'transaction_status': row[7],  # 交易状态
                    'notes': row[10],  # 备注
                    'bill_identifier': BILL_WECHAT,  # 账单类型
                    'uuid': row[8],  # 交易单号
                    'discount': False
                }
                records.append(record)
        except UnicodeDecodeError as e:
            logging.error("Unicode decode error at row=%s: %s", row, e)
        except Exception as e:
            logging.error("Unexpected error: %s", e)

        return records


def wechatpay_ignore(self, data):
    if data["bill_identifier"] == BILL_WECHAT:
        return data["transaction_status"] in ["已全额退款", "对方已退还"]
    # data["transaction_status"].startswith("已退款")


def wechatpay_get_expense_account(self, assets, ownerid):
    key = self.key
    if key in self.key_list:
        account_instance = Assets.objects.filter(key=key, owner_id=ownerid, enable=True).first()
        return account_instance.assets
    elif '(' in key and ')' in key:
        digits = key.split('(')[1].split(')')[0]  # 提取 account 中的数字部分，例如中信银行信用卡(6428) -> 6428
        if digits in self.key_list:  # 判断提取到的数字是否在列表中
            account_instance = Assets.objects.filter(key=digits, owner_id=ownerid).first()
            return account_instance.assets
        else:
            return ASSETS_OTHER  # 提取到的数字不在列表中，说明该账户不在数据库中，需要手动对账
    else:
        return ASSETS_OTHER


def wechatpay_get_income_account(self, assets, ownerid):
    key = self.key   # '中信银行(6428)'
    if self.status == "已转入零钱通":
        key = "零钱通"
    else:
        match = re.search(r'\((\d+)\)', key)
        if match:
            key = match.group(1)

    if key in self.key_list:  # 6428
        account_instance = Assets.objects.filter(key=key, owner_id=ownerid, enable=True).first()
        return account_instance.assets


def wechatpay_get_balance_account(self, data, assets, ownerid):
    # account = "Unknown-Account"  # 方便排查问题
    account = self.account
    if self.type == "零钱提现":
        for key in self.key_list:
            if key in data['counterparty']:
                account_instance = Assets.objects.filter(key=key, owner_id=ownerid, enable=True).first()
                account = account_instance.assets
                return account
        account = ASSETS_OTHER
    elif self.type == "零钱充值":
        account = assets["WECHATPAY"]
    elif self.type == "零钱通转出":
        index = data['transaction_category'].find("到")
        result = data['transaction_category'][index + 1:]  # 取来自之后的所有数据，例如"建设银行(5522)"
        for key in self.key_list:
            if key in result:
                account_instance = Assets.objects.filter(key=key, owner_id=ownerid, enable=True).first()
                account = account_instance.assets
                return account
        account = ASSETS_OTHER
    elif self.type == "转入零钱通":
        account = assets["WECHATFUND"]
    elif self.type == "信用卡还款":
        result = data['payment_method']
        for key in self.key_list:
            if key in result:
                account_instance = Assets.objects.filter(key=key, owner_id=ownerid, enable=True).first()
                account = account_instance.assets
                return account
            else:
                account = ASSETS_OTHER
    elif self.type == "购买理财通":
        result = data['payment_method'] + "储蓄卡"  # 目前无法区分同一家银行的多张储蓄卡
        for full in self.full_list:
            if result in full:
                account_instance = Assets.objects.filter(full=full, owner_id=ownerid, enable=True).first()
                account = account_instance.assets
                return account
    return account


def wechatpay_get_balance_expense(self, data, assets, ownerid):
    # expend = "Unknown-Expend"  # 方便排查问题
    expend = self.expend
    if self.type == "零钱提现":
        expend = assets["WECHATPAY"]
    elif self.type == "零钱充值":
        for key in self.key_list:
            if key in data['counterparty']:
                expend_instance = Assets.objects.filter(key=key, owner_id=ownerid, enable=True).first()
                expend = expend_instance.assets
                return expend
        expend = ASSETS_OTHER
    elif self.type == "零钱通转出":
        expend = assets["WECHATFUND"]
    elif self.type == "转入零钱通":
        index = data['transaction_category'].find("来自")
        result = data['transaction_category'][index + 2:]  # 取来自之后的所有数据，例如"建设银行(5522)"
        for key in self.key_list:
            if key in result:
                expend_instance = Assets.objects.filter(key=key, owner_id=ownerid, enable=True).first()
                expend = expend_instance.assets
                return expend
        expend = ASSETS_OTHER
    elif self.type == "信用卡还款":
        result = data['counterparty'][:data['counterparty'].index("还款")]  # 例如"华夏银行信用卡"
        for full in self.full_list:
            if result in full:
                account_instance = Assets.objects.filter(full=full, owner_id=ownerid, enable=True).first()
                account = account_instance.assets
                return account
    elif self.type == "购买理财通":
        expend = ASSETS_OTHER
    return expend


def wechatpay_get_type(data):
    return data['transaction_category'][:5]


def wechatpay_initalize_key(self, data):
    return data['payment_method']


def wechatpay_get_uuid(data):
    return data['uuid'].rstrip("\t")


def wechatpay_get_status(data):
    return "WeChat - " + data['transaction_status']


def wechatpay_get_amount(data):
    return "{:.2f}".format(float(data['amount'][1:]))  # 微信账单格式为"￥10.00"，需要转换


def wechatpay_get_note(data):
    if data['transaction_type'] == "/":  # 收支为/时，备注为交易类型
        return data['transaction_category']
    return data['commodity']


def wechatpay_get_tag(data):
    notes = wechatpay_get_note(data)
    if "#" in notes:
        return "#" + notes.split("#")[1].strip()
    elif "^" in notes:
        return "^" + notes.split("^")[1].strip()
    else:
        return None


def wechatpay_get_commission(data):
    return data['notes'][4:]


def wechatpay_get_discount(data):
    return data['discount']


IgnoreData.wechatpay_ignore = wechatpay_ignore