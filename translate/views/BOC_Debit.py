import re

import pdfplumber
from mydemo.utils.tools import time_to_timestamp
from translate.models import Assets
from translate.utils import PaymentStrategy, BILL_BOC_DEBIT

boc_debit_sourcefile_identifier = "中国银行交易流水明细清单"
boc_debit_csvfile_identifier = "中国银行储蓄卡账单明细"


class BocDebitStrategy(PaymentStrategy):
    """
    记账日期row[0],记账时间row[1],币别row[2],金额row[3],余额row[4],交易名称row[5],渠道row[6],网点名称row[7],       附言row[8],      对方账户名row[9],  对方卡号/账号row[10],对方开户行row[11]
    2024-03-18,   10:19:28,    人民币,    -11.00,    4853.00,  网上快捷支付,   银企对接,   -------------------,财付通-扫二维码付款,财付通-扫二维码付款,Z2004944000010N,   -------------------
    """

    def get_data(self, bill, card):
        row = 0
        while row < 1:
            next(bill)
            row += 1
        list = []
        try:
            for row in bill:
                time = row[0] + " " + row[1]
                currency = row[5]  # 交易类型
                object = row[9]  # 交易对方
                commodity = row[2]  # 商品
                type = "支出" if "-" in row[3] else "收入"  # 收支
                amount = row[3].replace("-", "") if "-" in row[3] else row[3]  # 金额
                way = "中国银行储蓄卡(" + card + ")"  # 支付方式
                status = BILL_BOC_DEBIT + " - 交易成功"  # 交易状态
                notes = row[8]  # 备注
                bill = BILL_BOC_DEBIT
                uuid = time_to_timestamp(time)
                balance = row[4]
                card_number = row[10]
                bank = row[11]
                single_list = [time, currency, object, commodity, type, amount, way, status, notes, bill, uuid, balance,
                               card_number, bank]
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


def boc_debit_pdf_convert_to_string(file, password):
    """接收PDF文件，返回字符串

    Args:
        file(_type_): PDF文件
        password (str): PDF文件的密码，如果文件受保护

    Returns:
        string: 以List形式返回
    """
    with pdfplumber.open(file, password=password) as pdf:
        content = []
        for page in pdf.pages:
            content += page.extract_tables()

    return content


def boc_debit_string_convert_to_csv(data, card_number):
    """接收字符串，返回CSV格式文件

    Args:
        data (string): _description_
        card_number (string): 储蓄卡/信用卡 完整的卡号

    Returns:
        csv: _description_
    """
    output_lines = [boc_debit_csvfile_identifier + " 卡号: " + card_number]

    # 打印头部行并添加至结果列表
    header = data[0][0]
    output_lines.append(",".join(header))

    # 对每个block中的交易记录进行处理
    for block in data:
        transactions = block[1:]
        for transaction in transactions:
            # 处理数据: 移除数字中的逗号, 替换附言中的换行符
            processed_transaction = [
                field.replace(',', '').replace('\n', '') if isinstance(field, str) else field
                for field in transaction
            ]
            # 添加处理后的单行交易记录至结果列表
            output_lines.append(",".join(processed_transaction))

    # 将最终的结果列表转换为一个字符串
    final_output = "\n".join(output_lines)

    return final_output


def boc_debit_get_uuid(data):
    return data[10]


def boc_debit_get_status(data):
    return data[7]


def boc_debit_get_amount(data):
    return "{:.2f} CNY".format(float(data[5]))


def boc_debit_get_notes(data):
    return data[8]


def boc_debit_init_key(data):
    return data[6]


def boc_debit_get_account(self, ownerid):
    key = self.key
    if key in self.full_list:
        account_instance = Assets.objects.filter(full=key, owner_id=ownerid).first()
        return account_instance.assets


def boc_debit_get_card_number(content):
    """
    从账单文件中获取中国银行卡号
    """
    boc_debit_card_number = re.search(r'\d{19}', content).group()
    return boc_debit_card_number
