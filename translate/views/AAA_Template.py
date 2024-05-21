import logging

from translate.utils import InitStrategy, IgnoreData

bank_type_sourcefile_identifier = "xxxxxxxxxx"  # 能唯一标识所属银行及账单类型的原始上传文件
bank_type_csvfile_identifier = "xx银行xx卡账单明细"  # 能唯一标识所属银行及账单类型


class BankTypeInitStrategy(InitStrategy):
    def init(self, bill, **kwargs):
        import itertools
        bill = itertools.islice(bill, 1, None)  # 默认跳过首行
        records = []
        try:
            for row in bill:
                record = {
                    'transaction_time': '/',  # 交易发生的时间
                    'transaction_category': '/',  # 交易类型
                    'counterparty': '/',  # 发生交易的对方
                    'commodity': '/',  # 商品
                    'transaction_type': '/',  # 收支类型（收入/支出/不计收支）
                    'amount': '/',  # 金额
                    'payment_method': '/',  # 使用什么进行支付（银行卡、储蓄卡、支付宝等）
                    'transaction_status': '/',  # 交易状态
                    'notes': '/',  # 备注
                    'bill_identifier': '/',  # 唯一标识账单（用于区分传入的各个账单以调用不同的函数处理）
                    'uuid': '/',  # 每条记录的唯一标识
                    'balance': '/',  # 发生交易后的储蓄卡余额
                    'card_number': "对方卡号",  # 发生交易的对方卡号
                    'counterparty_bank': "所属银行"  # 发生交易的对方银行开户行
                }
                records.append(record)
        except UnicodeDecodeError as e:
            logging.error("Unicode decode error at row=%s: %s", row, e)
        except Exception as e:
            logging.error("Unexpected error: %s", e)

        return records


def bank_type_ignore(self, data, bank_type_ignore):
    pass


def bank_type_pdf_convert_to_string(file, password):
    """从PDF文件中提取表格数据，并将其转换为列表格式

    Args:
        file (str): 要处理的PDF文件的路径
        password (str): PDF文件的密码（如果有）

    Returns:
        list: 包含从PDF文件中提取的表格数据的列表
    """
    pass


def bank_type_xls_convert_to_string(file):
    """读取Excel文件并将其转换为列表格式

    Args:
        file (str): Excel文件的路径

    Returns:
        list: 包含Excel文件数据的列表
    """
    pass


def bank_type_string_convert_to_csv(data, card_number):
    """将列表数据转换为CSV格式

    Args:
        data (list): 包含借记卡数据的列表
        card_number (str): 银行卡号

    Returns:
        str: 转换后的CSV格式字符串
    """
    pass


def bank_type_get_uuid(data):
    """接收字符串，返回uuid用于唯一标识

    Args:
        data (string): _description_

    Returns:
        uuid: 若有账单条目唯一识别则直接使用，若无则根据时间字符串转换为时间戳
    """
    pass


def bank_type_get_status(data):
    """接收字符串，返回条目状态

    Args:
        data (string): _description_

    Returns:
        status: 各交易状态（支付成功、退款成功等）
    """
    pass


def bank_type_get_amount(data):
    """接收字符串，返回金额

    Args:
        data (string): _description_

    Returns:
        amount: 金额
    """
    pass


def bank_type_get_note(data):
    """接收字符串，返回备注

    Args:
        data (string): _description_

    Returns:
        note:备注
    """
    pass


def bank_type_get_tag(data):
    """支付宝、微信识别 "#" 用于添加tag标签 

    Args:
        data (_type_): _description_
    """
    pass


def bank_type_get_commission(data):
    """用于计算利息

    Args:
        data (_type_): _description_
    """
    pass


def bank_type_init_key(data):
    """从账单文件中获取能唯一标识的关键字

    如"中国银行储蓄卡(0814)"，与"映射管理" "资产映射"中的"账户"一致

    用于在所有账户中找到对应的映射账户

    Args:
        data (string): _description_

    Returns:
        key (string):
    """
    pass


def bank_type_get_expense(self, ownerid):
    """根据bank_type_init_key得到的key来查找对应的expense

    Args:
        self (string): _description_
        ownerid (string): _description_

    Returns:
        expense: _description_
    """
    pass


def bank_type_get_account(self, ownerid):
    """根据所有者ID获取账户资产信息

    Args:
        ownerid: 账户所有者的ID

    Returns:
        float: 账户资产信息
    """
    pass


def bank_type_get_card_number(content):
    """从内容中提取卡号

    Args:
        content (str): 包含借记卡号的内容

    Returns:
        str: 提取的卡号
    """
    pass


IgnoreData.bank_type_ignore = bank_type_ignore