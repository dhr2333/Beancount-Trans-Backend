from project.apps.translate.services.init.strategies.base_bill_init_strategy import InitStrategy
from typing import List, Dict, Any
from project.apps.translate.utils import BILL_BOC_DEBIT
import logging
import csv
import itertools


class BOCDebitInitStrategy(InitStrategy):
    """中国银行借记卡账单初始化策略"""

    SOURCE_FILE_IDENTIFIER = "中国银行交易流水明细清单"
    HEADER_MARKER = "中国银行储蓄卡账单明细"
    SKIP_ROWS = 1

    def init(self, bill: Any, **kwargs) -> List[Dict[str, Any]]:
        csv_reader = csv.reader(bill)
        data_rows = itertools.islice(csv_reader, self.SKIP_ROWS, None)  # 跳过前指定行
        records = []

        card = kwargs.get('card_number', None)
        try:
            for row in data_rows:
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

    @classmethod
    def identifier(cls, first_line: str) -> bool:
        return cls.HEADER_MARKER in first_line
