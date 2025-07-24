# project/apps/translate/services/parsing/filters.py
import logging
from translate.utils import IgnoreData
from typing import Dict, List


logger = logging.getLogger(__name__)

class TransactionFilter:
    """交易记录过滤器"""
    
    def __init__(self, args: Dict):
        self.args = args
        self.ignore_data = IgnoreData(None)
    
    def apply_bill_filters(self, bill_data: List[Dict]) -> List[Dict]:
        """应用账单级过滤器"""
        filtered_data = []
        
        # 余额过滤
        if self.args["balance"] is True:
            bill_data = self.ignore_data.balance(bill_data)
        
        # 账单特定过滤器
        for row in bill_data:
            if not self._should_ignore_row(row):
                filtered_data.append(row)
            # else: 
            #     # 日志输出被忽略的条目
            #     logger.info(f"Ignored row: {row}")
        
        return filtered_data
    
    def apply_entry_filters(self, entries: List[Dict]) -> List[Dict]:
        """应用记录级过滤器"""
        return [entry for entry in entries if not self._should_ignore_entry(entry)]
    
    def _should_ignore_row(self, row: Dict) -> bool:
        """判断是否忽略原始记录"""
        return (
            self.ignore_data.wechatpay_ignore(row) or
            self.ignore_data.alipay_ignore(row) or
            self.ignore_data.alipay_fund_ignore(row) or
            self.ignore_data.cmb_credit_ignore(row, self.args.get("cmb_credit_ignore", "")) or
            self.ignore_data.boc_debit_ignore(row, self.args.get("boc_debit_ignore", ""))
        )
    
    def _should_ignore_entry(self, entry: Dict) -> bool:
        """判断是否忽略解析后的entry"""
        if self.ignore_data.empty(entry):
            return False