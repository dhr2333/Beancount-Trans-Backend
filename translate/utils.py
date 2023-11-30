import logging

transaction_status = {
    "wechatpay": ["支付成功", "已存入零钱", "已转账", "对方已收钱", "已到账", "已全额退款", "对方已退还", "提现已到账",
                  "充值完成", "充值成功", "已收钱"],
    "alipay": ["交易成功", "交易关闭", "退款成功", "支付成功", "代付成功", "还款成功", "已关闭", "解冻成功",
               "信用服务使用成功"]
}


class PaymentStrategy:
    def get_data(self, bill):
        raise NotImplementedError()


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
                bill = "wechat"  # 账单(用于区分传入的各个账单以调用不同的函数处理)
                uuid = row[8]  # 交易单号
                single_list = [time, type, object, commodity, balance, amount, way, status, notes, bill, uuid]
                list.append(single_list)
        except UnicodeDecodeError:
            logging.error("error row = ", row)
        return list


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


def get_initials_bill(bill):
    """Get the initials of the bill's name."""
    first_line = next(bill)[0]
    if isinstance(first_line, str) and "微信支付账单明细" in first_line:
        strategy = WeChatPayStrategy()
    elif isinstance(first_line,
                    str) and "------------------------------------------------------------------------------------" in first_line:
        strategy = AliPayStrategy()
    else:
        strategy = None
        logging.error("当前账单不支持，请检查账单格式是否正确")
    return strategy.get_data(bill)
