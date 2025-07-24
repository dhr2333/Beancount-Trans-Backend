# project/apps/translate/services/init/strategies/alipay_init_strategy.py
from translate.services.init.strategies.base_bill_init_strategy import InitStrategy
from typing import List, Dict, Any
from translate.utils import BILL_ALI
import logging
import csv
import itertools


class AlipayInitStrategy(InitStrategy):
    """支付宝账单初始化策略"""
    
    HEADER_MARKER = "-" * 84
    SKIP_ROWS = 24
    
    def init(self, bill: Any, **kwargs) -> List[Dict[str, Any]]:
        csv_reader = csv.reader(bill)
        data_rows = itertools.islice(csv_reader, self.SKIP_ROWS, None)  # 跳过前指定行
        records = []

        try:
            for row in data_rows:
                transaction_type = "/" if row[5] == "不计收支" else row[5]
                payment_method = "余额" if row[7].strip() == '' else row[7].strip()
                notes = "/" if row[11].strip() == '' else row[11].strip()

                record = {
                    'transaction_time': row[0].strip(),  # 交易时间
                    'transaction_category': row[1].strip(),  # 交易类型
                    'counterparty': row[2].strip(),  # 交易对方
                    'commodity': row[4].strip(),  # 商品
                    'transaction_type': transaction_type.strip(),  # 收支类型（收入/支出/不计收支）
                    'amount': float(row[6].strip()),  # 金额
                    'payment_method': payment_method.split('&')[0],  # 支付方式
                    'transaction_status': row[8].strip(),  # 交易状态
                    'notes': notes,  # 备注
                    'bill_identifier': BILL_ALI,  # 账单类型
                    'uuid': row[9].strip(),  # 交易单号
                    'discount': True if "&" in payment_method else False  # 支付方式
                }
                records.append(record)

        except UnicodeDecodeError as e:
            logging.error(f"Unicode decode error at row={row}: {str(e)}")
        except Exception as e:
            logging.error(f"Unexpected error: {str(e)}")

        return records
    
    @classmethod
    def identifier(cls, first_line: str) -> bool:
        """判断是否为支付宝账单"""
        return cls.HEADER_MARKER in first_line


    # def get_uuid(self, data: Dict) -> str:
    #     return data.get("uuid", "")
    
    # def get_status(self, data: Dict) -> str:
    #     return data.get("status", "未知")
    
    # def get_note(self, data: Dict) -> str:
    #     return data.get("note", "")
    
    # def get_amount(self, data: Dict) -> str:
    #     return str(data.get("amount", 0.0))
    
    # def get_tag(self, data: Dict) -> str:
    #     return data.get("tag", "")
    
    # def get_balance(self, data: Dict) -> str:
    #     return str(data.get("balance", 0.0))
    
    # def get_commission(self, data: Dict) -> str:
    #     return str(data.get("commission", 0.0))
    
    # def get_installment_granularity(self, data: Dict) -> str:
    #     return data.get("installment_granularity", "")
    
    # def get_installment_cycle(self, data: Dict) -> int:
    #     return int(data.get("installment_cycle", 0))
    
    # def get_discount(self, data: Dict) -> bool:
    #     return bool(data.get("discount", False))


# class AlipayInitFactory(InitFactory):
#     """支付宝账单初始化工厂"""
#     def create_strategy(self) -> InitStrategy:
#         return AlipayInitStrategy()