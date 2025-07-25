# project/apps/translate/services/init/strategies/wechat_init_strategy.py
from translate.services.init.strategies.base_bill_init_strategy import InitStrategy
from typing import List, Dict, Any
from translate.utils import BILL_WECHAT
import logging
import csv
import itertools


class WeChatPayInitStrategy(InitStrategy):
    """微信账单初始化策略"""

    HEADER_MARKER = "微信支付账单明细,,,,,,,,"
    SKIP_ROWS = 16

    def init(self, bill: Any, **kwargs) -> List[Dict[str, Any]]:
        csv_reader = csv.reader(bill)
        data_rows = itertools.islice(csv_reader, self.SKIP_ROWS, None)  # 跳过前指定行
        records = []

        try:
            for row in data_rows:
                record = {
                    'transaction_time': row[0],  # 交易时间
                    'transaction_category': row[1],  # 交易类型
                    'counterparty': row[2],  # 交易对方
                    'commodity': row[3],  # 商品
                    'transaction_type': row[4],  # 收支类型（收入/支出/不计收支）
                    'amount': row[5],  # 金额
                    'payment_method': row[6],  # 支付方式
                    'transaction_status': row[7],  # 交易状态
                    'notes': row[10],  # 备注
                    'bill_identifier': BILL_WECHAT,  # 账单类型
                    'uuid': row[8],  # 交易单号
                    'discount': False
                }
                records.append(record)

        except UnicodeDecodeError as e:
            logging.error("Unicode decode error at row=%s: %s", row, e)
        except Exception as e:
            logging.error("Unexpected error: %s", e)

        return records
    
    @classmethod
    def identifier(cls, first_line: str) -> bool:
        """判断是否为微信账单"""
        return cls.HEADER_MARKER in first_line