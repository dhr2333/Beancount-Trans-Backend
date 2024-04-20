import re
from datetime import datetime


def time_to_timestamp(time_str):
    # 将时间字符串转换为datetime对象
    dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
    # 转换datetime为时间戳
    timestamp = int(dt.timestamp())
    return timestamp


def timestamp_to_time(timestamp):
    # 从时间戳转换回datetime对象
    dt = datetime.fromtimestamp(timestamp)
    # 格式化datetime为字符串
    time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
    return time_str


def get_card_number(content):
    """
    从账单文件中获取该账单对应的银行卡号
    """
    boc_debit_card_number = boc_debit_get_card_number(content)
    return boc_debit_card_number


def boc_debit_get_card_number(content):
    """
    从账单文件中获取中国银行卡号
    """
    boc_debit_card_number = re.search(r'\d{19}', content).group()
    return boc_debit_card_number
