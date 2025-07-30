from project.apps.translate.services.init.strategies.base_bill_init_strategy import InitStrategy
from typing import List, Dict, Any
from project.apps.translate.utils import BILL_CCB_DEBIT
from datetime import datetime
import logging
import csv
import itertools


class CCBDebitInitStrategy(InitStrategy):
    """中国建设银行借记卡账单初始化策略"""

    SOURCE_FILE_IDENTIFIER = "中国建设银行个人活期账户全部交易明细"
    HEADER_MARKER = "中国建设银行储蓄卡账单明细"
    SKIP_ROWS = 1

    def init(self, bill: Any, **kwargs) -> List[Dict[str, Any]]:
        csv_reader = csv.reader(bill)
        data_rows = itertools.islice(csv_reader, self.SKIP_ROWS, None)  # 跳过前指定行
        records = []

        card = kwargs.get('card_number', None)
        try:
            for row in data_rows:
                record = {
                    'transaction_time': datetime.strptime(row[3], '%Y%m%d').strftime('%Y-%m-%d %H:%M:%S'),  # 交易时间
                    'transaction_category': row[0],  # 交易类型
                    'counterparty': row[8],  # 交易对方
                    'commodity': row[6],  # 商品
                    'transaction_type': "支出" if "-" in row[4] else "收入",  # 收支类型（收入/支出/不计收支）
                    'amount': row[4].replace("-", "") if "-" in row[4] else row[4],  # 金额
                    'payment_method': "中国建设银行储蓄卡(" + card + ")",  # 支付方式
                    'transaction_status': BILL_CCB_DEBIT + " - 交易成功",  # 交易状态
                    'notes': row[6],  # 备注
                    'bill_identifier': BILL_CCB_DEBIT,  # 账单类型
                    'balance': row[5],
                    'card_number': row[7],
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
