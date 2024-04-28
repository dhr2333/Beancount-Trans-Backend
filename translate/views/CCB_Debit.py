import re

from translate.utils import PaymentStrategy, BILL_CCB_DEBIT
from mydemo.utils.tools import time_to_timestamp
from translate.models import Assets
from datetime import datetime

ccb_debit_sourcefile_identifier = "中国建设银行个人活期账户全部交易明细"  # 能唯一标识所属银行及账单类型的原始上传文件
ccb_debit_csvfile_identifier = "中国建设银行储蓄卡账单明细"  # 能唯一标识所属银行及账单类型


class CcbDebitStrategy(PaymentStrategy):
    """
    摘要row[0], 币别row[1],钞汇row[2],交易日期row[3],交易金额row[4],账户余额row[5],交易地点row[6],对方账号row[7],户名row[8]
    支付机构提现,   人民币元,        钞,    20230303,       +10.00,        10.00,    零钱通提现,    243300133,财付通支付科技有限公司
    """
    def get_data(self, bill, card):
        """根据csv文件的内容对字段进行整合

        Args:
            bill(csv.reader):

        Returns:
            list: _description_
        """
        row = 0
        while row < 1:
            next(bill)
            row += 1
        list = []
        try:
            for row in bill:
                time = datetime.strptime(row[3], '%Y%m%d').strftime('%Y-%m-%d %H:%M:%S')
                currency = row[0]  # 交易类型，当object和card_number为"（空）"时object = currency
                object = row[8]  # 交易对方
                commodity = row[6]  # 商品
                type = "支出" if "-" in row[4] else "收入"  # 收支
                amount = row[4].replace("-", "") if "-" in row[4] else row[4]  # 金额
                way = "中国建设银行储蓄卡(" + card + ")"  # 支付方式
                status = BILL_CCB_DEBIT + " - 交易成功"  # 交易状态
                notes = row[6]  # 备注
                bill = BILL_CCB_DEBIT
                uuid = time_to_timestamp(time)
                balance = row[5]
                card_number = row[7]  # 对方卡号
                single_list = [time, currency, object, commodity, type, amount, way, status, notes, bill, uuid, balance,
                               card_number]
                new_list = []
                for item in single_list:
                    new_item = str(item).strip()
                    new_list.append(new_item)
                list.append(new_list)
        except UnicodeDecodeError:
            print("UnicodeDecodeError error row = ", row)
        except:
            print("error row = ", row)
        return list


def ccb_debit_pdf_convert_to_string(file, card_number):
    """接收PDF文件，返回字符串

    Args:
        file(_type_): PDF文件

    Returns:
        string: 以List形式返回
    """
    pass


def ccb_debit_xls_convert_to_string(file):
    """
    从Excel文件读取数据并转换为列表格式。

    Args:
        file(str): Excel文件的路径

    Returns:
        list: 包含Excel文件中所有数据的列表
    """
    import pandas as pd

    # 读取Excel文件
    data = pd.read_excel(file, header=None)
    # 将DataFrame转换为嵌套列表
    data_list = data.values.tolist()
    return data_list


def ccb_debit_string_convert_to_csv(data):
    """接收字符串，返回CSV格式文件

    Args:
        data (string): _description_
        card_number (string): 储蓄卡/信用卡 完整的卡号

    Returns:
        csv: _description_
    """
    import pandas as pd

    # 提取标题和账号信息
    title = data[0][4].replace('个人活期账户全部交易明细', '储蓄卡账单明细')
    card_number = data[1][1].split(':')[1]

    # 构造输出字符串
    output = f"{title} 卡号: {card_number}\n"

    # 添加列名
    columns = data[2]
    output += f"{columns[1]},{columns[2]},{columns[3]},{columns[4]},{columns[5]},{columns[6]},{columns[7].split('/')[0]},对方账号,户名\n"

    # 添加数据行
    for row in data[3:]:
        cleaned_row = [str(item).replace(',', '') if not pd.isna(item) else '（空）' for item in row]
        # 处理交易金额，为正数添加'+'
        transaction_amount = cleaned_row[5]
        if transaction_amount.startswith('-'):
            transaction_amount = transaction_amount.replace('-', '-')
        else:
            transaction_amount = '+' + transaction_amount

        cleaned_row[5] = transaction_amount  # 更新交易金额的格式

        account, name = (cleaned_row[8].split('/') + ['（空）', '（空）'])[:2]  # 处理对方账号与户名字段

        output += f"{cleaned_row[1]},{cleaned_row[2]},{cleaned_row[3]},{cleaned_row[4]},{transaction_amount},{cleaned_row[6]},{cleaned_row[7]},{account},{name}\n"

    # 输出结果
    return output


def ccb_debit_get_uuid(data):
    """接收字符串，返回uuid用于唯一标识

    Args:
        data (string): _description_

    Returns:
        uuid: 若有账单条目唯一识别则直接使用，若无则根据时间字符串转换为时间戳
    """
    return data[10]


def ccb_debit_get_status(data):
    """接收字符串，返回条目状态

    Args:
        data (string): _description_

    Returns:
        status: 各交易状态（支付成功、退款成功等）
    """
    return data[7]


def ccb_debit_get_amount(data):
    """接收字符串，返回金额

    Args:
        data (string): _description_

    Returns:
        amount: 金额
    """
    return "{:.2f} CNY".format(float(data[5]))


def ccb_debit_get_notes(data):
    """接收字符串，返回备注

    Args:
        data (string): _description_

    Returns:
        notes:备注
    """
    return data[8]


def ccb_debit_init_key(data):
    """从账单文件中获取能唯一标识的关键字

    如"中国银行储蓄卡(0814)"，与"映射管理" "资产映射"中的"账户"一致

    用于在所有账户中找到对应的映射账户

    Args:
        data (string): _description_

    Returns:
        key (string):
    """
    return data[6]


def ccb_debit_get_expense(self, ownerid):
    """根据bank_type_init_key得到的key来查找对应的expense

    Args:
        self (string): _description_
        ownerid (string): _description_

    Returns:
        expense: _description_
    """
    pass


def ccb_debit_get_account(self, ownerid):
    """根据bank_type_init_key得到的key来查找对应的account

    Args:
        self (string): _description_
        ownerid (string): _description_

    Returns:
        account: _description_
    """
    key = self.key
    if key in self.full_list:
        account_instance = Assets.objects.filter(full=key, owner_id=ownerid).first()
        return account_instance.assets


def ccb_debit_get_card_number(content):
    """
    从账单文件中获取银行卡号
    """
    ccb_debit_card_number = re.search(r'\d{19}', content).group()
    return ccb_debit_card_number
