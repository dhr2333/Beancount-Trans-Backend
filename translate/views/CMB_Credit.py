import csv
import io
import re
import logging

from datetime import datetime
from translate.models import Assets
from translate.utils import InitStrategy, IgnoreData, ASSETS_OTHER, BILL_CMB_CREDIT

cmb_credit_sourcefile_identifier = "CMB Credit Card Statement"
cmb_credit_csvfile_identifier = "招商银行信用卡账单明细"


class CmbCreditInitStrategy(InitStrategy):
    def init(self, bill, **kwargs):
        import itertools
        year = kwargs.get('year', None)
        bill = itertools.islice(bill, 2, None)
        records = []
        try:
            for row in bill:
                record = {
                    'transaction_time': datetime.strptime(f'{year}/{row[0]}', '%Y/%m/%d').strftime(f'{year}-%m-%d 00:00:00'),  # 交易时间
                    'transaction_category': "商户消费",
                    'counterparty': row[2],  # 交易对方
                    'commodity': "/",  # 商品
                    'transaction_type': "收入" if "-" in row[3] else "支出",  # 收支类型（收入/支出/不计收支）
                    'amount': row[3].replace("-", "") if "-" in row[3] else row[3],  # 金额
                    'payment_method': "招商银行信用卡(" + row[4] + ")",  # 支付方式
                    'transaction_status': BILL_CMB_CREDIT + " - 交易成功",  # 交易状态
                    'bill_identifier': BILL_CMB_CREDIT,  # 账单类型
                }
                records.append(record)
        except UnicodeDecodeError as e:
            logging.error("Unicode decode error at row=%s: %s", row, e)
        except Exception as e:
            logging.error("Unexpected error: %s", e)

        return records


def cmb_credit_ignore(self, data, cmb_credit_ignore):
    if data['bill_identifier'] == BILL_CMB_CREDIT and ("支付宝" in data['counterparty'] or "财付通" in data['counterparty']):
        return cmb_credit_ignore == "true"


def cmb_credit_pdf_convert_to_csv(content):
    """接收字符串，处理为需要的格式，返回字符串

    Args:
        content (string): _description_

    Returns:
        _type_: _description_
    """
    lines = content.split('\n')
    date_string = None

    # 提取日期字符串
    date_match = re.search(r'CMB Credit Card Statement \((\d{4}\.\d{2})\)', content)
    if date_match:
        date_string = date_match.group(1)
    output = io.StringIO()
    csv_writer = csv.writer(output)
    written_data = []  # 用于保存已写入的数据
    if date_string:
        csv_writer.writerow([f'{date_string} {cmb_credit_csvfile_identifier}'])
    else:
        csv_writer.writerow([cmb_credit_csvfile_identifier])
    csv_writer.writerow(['交易日', '记账日', '交易摘要', '人民币金额', '卡号末四位', '交易地金额'])
    pattern = r'(\s*\d{2}/\d{2})\s+(\d{2}/\d{2})\s+(.*?)\s+(-?\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s+(\d{4})\s+(-?\d{1,3}(?:,\d{3})*(?:\.\d{2})?)'
    for line in lines:
        line = re.sub(r'CMB Credit Card Statement \(\d{4}\.\d{2}\)', '', line)
        match = re.match(pattern, line)
        if match:
            transaction_date = match.group(1).strip()
            posting_date = match.group(2)
            description = match.group(3)
            rmb_amount = match.group(4).replace(',', '')
            card_last_four_digits = match.group(5)
            foreign_amount = match.group(6).replace(',', '')

            written_data.append(
                [transaction_date, posting_date, description, rmb_amount, card_last_four_digits, foreign_amount])
            csv_writer.writerow(
                [transaction_date, posting_date, description, rmb_amount, card_last_four_digits, foreign_amount])

    output.seek(0)  # 将文件指针移回开头
    result = output.getvalue()  # 获取结果字符串
    output.close()  # 关闭文件对象
    return result


def cmb_credit_get_status(data):
    return data['transaction_status']


def cmb_credit_get_amount(data):
    return "{:.2f}".format(float(data['amount']))


def cmb_credit_get_note(data):
    return data['commodity']


def cmb_credit_init_key(data):
    return data['payment_method']


def cmb_credit_get_account(self, ownerid):
    key = self.key
    if key in self.key_list:
        account_instance = Assets.objects.filter(key=key, owner_id=ownerid, enable=True).first()
        return account_instance.assets
    elif '(' in key and ')' in key:
        digits = key.split('(')[1].split(')')[0]  # 提取 account 中的数字部分，例如中信银行信用卡(6428) -> 6428
        if digits in self.key_list:  # 判断提取到的数字是否在列表中
            account_instance = Assets.objects.filter(key=digits, owner_id=ownerid, enable=True).first()
            return account_instance.assets
        else:
            return ASSETS_OTHER  # 提取到的数字不在列表中，说明该账户不在数据库中，需要手动对账

IgnoreData.cmb_credit_ignore = cmb_credit_ignore