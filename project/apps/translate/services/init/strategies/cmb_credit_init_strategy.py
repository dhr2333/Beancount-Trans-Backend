from translate.services.init.strategies.base_bill_init_strategy import InitStrategy
from typing import List, Dict, Any
from translate.utils import BILL_CMB_CREDIT
from datetime import datetime
import logging
import csv
import itertools


class CMBCreditInitStrategy(InitStrategy):
    """招商银行信用卡账单初始化策略"""

    HEADER_MARKER = "招商银行信用卡账单明细"
    SKIP_ROWS = 2

    def init(self, bill: Any, **kwargs) -> List[Dict[str, Any]]:
        csv_reader = csv.reader(bill)
        data_rows = itertools.islice(csv_reader, self.SKIP_ROWS, None)  # 跳过前指定行
        records = []

        year = kwargs.get('year', None)
        try:
            for row in data_rows:
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

    @classmethod
    def identifier(cls, first_line: str) -> bool:
        return cls.HEADER_MARKER in first_line
