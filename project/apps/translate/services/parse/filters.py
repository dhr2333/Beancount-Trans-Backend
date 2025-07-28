# project/apps/translate/services/parse/filters.py
import logging
from project.apps.translate.services.parse.ignore_registry import registry
from typing import Dict, List

logger = logging.getLogger(__name__)

class TransactionFilter:
    """交易记录过滤器"""
    
    def __init__(self, args: Dict, bill_type: str):
        self.args = args
        self.bill_type = bill_type
    
    def apply_pre_filters(self, bill_data: List[Dict]) -> List[Dict]:
        """应用账单级预过滤"""
        # 1. 通用过滤（如余额过滤）
        if self.args["balance"] is True:
            bill_data = self._apply_balance_filter(bill_data)
        
        # 2. 账单特定过滤
        pre_filter = registry.get_pre_filter(self.bill_type)
        if not pre_filter:
            return bill_data
        
        return [row for row in bill_data if not pre_filter(row, self.args)]
    
    def apply_post_filters(self, entries: List[Dict]) -> List[Dict]:
        """应用记录级后过滤"""
        post_filter = registry.get_post_filter(self.bill_type)
        if not post_filter:
            return entries
            
        return [entry for entry in entries if not post_filter(entry, self.args)]
    
    def _apply_balance_filter(self, bill_data: List[Dict]) -> List[Dict]:
        """余额过滤通用实现"""
        from datetime import datetime

        # 将字符串日期转换为 datetime 对象
        for record in bill_data:
            record["transaction_time"] = datetime.strptime(record["transaction_time"], "%Y-%m-%d %H:%M:%S")
        # 以天为单位找到每组中时间最晚的记录
        unique_days = {}
        for record in bill_data:
            date_key = record["transaction_time"].date()
            if date_key not in unique_days or record["transaction_time"] > unique_days[date_key]["transaction_time"]:
                unique_days[date_key] = record
        # 提取结果并保证输入和输出的格式不变
        result = list(unique_days.values())
        # 将 transaction_time 转换回字符串
        for record in result:
            record["transaction_time"] = record["transaction_time"].strftime("%Y-%m-%d %H:%M:%S")
        return result
