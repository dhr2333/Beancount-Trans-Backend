from translate.utils import PaymentStrategy


class BankTypeStrategy(PaymentStrategy):
    def get_data(self, bill):
        """根据csv文件的内容对字段进行整合

        Args:
            bill(csv.reader):

        Returns:
            list: _description_
        """
        pass


def bank_type_pdf_convert_to_string(file):
    """接收PDF文件，返回字符串

    Args:
        file(_type_): PDF文件

    Returns:
        string: 以List形式返回
    """
    pass


def bank_type_string_convert_to_csv(data, card_number):
    """接收字符串，返回CSV格式文件

    Args:
        data (string): _description_
        card_number (string): 储蓄卡/信用卡 完整的卡号

    Returns:
        csv: _description_
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
    """根据bank_type_init_key得到的key来查找对应的account

    Args:
        self (string): _description_
        ownerid (string): _description_

    Returns:
        account: _description_
    """
    pass
