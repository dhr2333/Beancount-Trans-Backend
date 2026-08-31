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
        pre_filters = registry.get_pre_filter(self.bill_type)
        if not pre_filters:
            return bill_data

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
