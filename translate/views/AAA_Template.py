import re

from translate.utils import PaymentStrategy

bank_type_sourcefile_identifier = "xxxxxxxxxx"  # 能唯一标识所属银行及账单类型的原始上传文件
bank_type_csvfile_identifier = "xx银行xx卡账单明细"  # 能唯一标识所属银行及账单类型


class BankTypeStrategy(PaymentStrategy):
    def get_data(self, bill):
        """根据CSV文件的内容对字段进行整合，转换为特定格式的列表

        Args:
            bill (csv.reader): 包含银行交易数据的csv.reader对象

        Returns:
            list: 包含整合后的银行交易数据的列表，每个元素为包含特定字段的列表

        Raises:
            UnicodeDecodeError: 若遇到编码错误时抛出异常
            Exception: 其他异常情况下抛出异常
        """
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


def bank_type_get_notes(data):
    """接收字符串，返回备注

    Args:
        data (string): _description_

    Returns:
        notes:备注
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
