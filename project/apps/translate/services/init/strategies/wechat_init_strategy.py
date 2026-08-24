# project/apps/translate/services/init/strategies/wechat_init_strategy.py
from project.apps.translate.services.init.strategies.base_bill_init_strategy import InitStrategy
from typing import List, Dict, Any
from project.apps.translate.utils import BILL_WECHAT
import logging
import csv
import re


class WeChatPayInitStrategy(InitStrategy):
    """微信账单初始化策略"""

    HEADER_MARKER = "微信支付账单明细,,,,,,,,"
    TRANSACTION_TIME_HEADER = "交易时间"
    DETAIL_LIST_MARKER = "微信支付账单明细列表"
    _DATETIME_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")

    def init(self, bill: Any, **kwargs) -> List[Dict[str, Any]]:
        csv_reader = csv.reader(bill)
        records = []
        data_started = False

        try:
            for row in csv_reader:
                if len(row) < 11:
                    continue
                row = [c.strip().strip("\t") if isinstance(c, str) else c for c in row]
                first_cell = row[0]

                if not data_started:
                    if first_cell == self.TRANSACTION_TIME_HEADER:
                        data_started = True
                    continue

                if not first_cell:
                    continue
                if self.DETAIL_LIST_MARKER in first_cell or first_cell.startswith("-"):
                    continue
                if not self._DATETIME_PATTERN.match(first_cell):
                    continue

                record = {
                    'transaction_time': first_cell,  # 交易时间
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
                    'merchant_order': row[9],  # 商户单号（转账/红包关联原单）
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
        """判断是否为微信账单（兼容旧版 CSV 首行多逗号与新版 xlsx 导出首格标题）。"""
        if cls.HEADER_MARKER in first_line:
            return True
        first_cell = first_line.split(",", 1)[0].strip().strip("\ufeff")
        return first_cell.startswith("微信支付账单明细")