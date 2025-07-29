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

        # 2. 获取预过滤规则
        pre_filters = registry.get_pre_filter(self.bill_type)
        if not pre_filters:
            return bill_data

        # 3. 应用预过滤规则
        return [
            row for row in bill_data
            if not any(
                filter_func(row, self.args)
                for filter_func in pre_filters
            )
        ]

    def apply_post_filters(self, entries: List[Dict]) -> List[Dict]:
        """应用记录级后过滤"""
        universal_filters = registry.get_post_universal_filters()
        if universal_filters:
            entries = [
                entry for entry in entries
                if not any(
                    filter_func(entry, self.args)
                    for filter_func in universal_filters
                )
            ]

        post_filters = registry.get_post_filter(self.bill_type)
        if not post_filters:
            return entries

        return [
            entry for entry in entries
            if not any(
                filter_func(entry, self.args)
                for filter_func in post_filters
            )
        ]

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
