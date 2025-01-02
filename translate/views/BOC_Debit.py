import re
import logging
import pdfplumber

from translate.models import Assets
from translate.utils import InitStrategy, IgnoreData, BILL_BOC_DEBIT

boc_debit_sourcefile_identifier = "中国银行交易流水明细清单"
boc_debit_csvfile_identifier = "中国银行储蓄卡账单明细"


class BocDebitInitStrategy(InitStrategy):
    def init(self, bill, **kwargs):
        import itertools

        card = kwargs.get('card_number', None)
        bill = itertools.islice(bill, 1, None)
        records = []
        try:
            for row in bill:
                record = {
                    'transaction_time': row[0] + " " + row[1],  # 交易时间
                    'transaction_category': row[5],  # 交易类型
                    'counterparty': row[5] if "-------------------" in row[9] else row[9],  # 交易对方
                    'commodity': row[2],  # 商品
                    'transaction_type': "支出" if "-" in row[3] else "收入" ,  # 收支类型（收入/支出/不计收支）
                    'amount': row[3].replace("-", "") if "-" in row[3] else row[3],  # 金额
                    'payment_method': "中国银行储蓄卡(" + card + ")",  # 支付方式
                    'transaction_status': BILL_BOC_DEBIT + " - 交易成功",  # 交易状态
                    'notes': row[8],  # 备注
                    'bill_identifier': BILL_BOC_DEBIT,  # 账单类型
                    'balance': row[4],
                    'card_number': row[10],
                    'counterparty_bank': row[11],
                }
                records.append(record)
        except UnicodeDecodeError as e:
            logging.error("Unicode decode error at row=%s: %s", row, e)
        except Exception as e:
            logging.error("Unexpected error: %s", e)

        return records


def boc_debit_ignore(self, data, boc_debit_ignore):
    if data['bill_identifier'] == BILL_BOC_DEBIT and ("支付宝" in data['counterparty'] or "财付通" in data['counterparty']):
        return boc_debit_ignore == "true"
    

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
    return data['uuid']


def boc_debit_get_status(data):
    return data['transaction_status']


def boc_debit_get_amount(data):
    return "{:.2f}".format(float(data['amount']))


def boc_debit_get_note(data):
    return data['notes']


def boc_debit_init_key(data):
    return data['payment_method']


def boc_debit_get_account(self, ownerid):
    key = self.key
    if key in self.full_list:
        account_instance = Assets.objects.filter(full=key, owner_id=ownerid).first()
        return account_instance.assets


def boc_debit_get_balance(data):
    return data['balance']
    
    
def boc_debit_get_card_number(content):
    """
    从账单文件中获取中国银行卡号
    """
    boc_debit_card_number = re.search(r'\d{19}', content).group()
    return boc_debit_card_number

IgnoreData.boc_debit_ignore = boc_debit_ignore