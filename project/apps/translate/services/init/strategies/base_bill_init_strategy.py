# project/apps/translate/services/init/strategies/base_bill_init_strategy.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class InitStrategy(ABC):
    @abstractmethod
    def init(self, bill: Any, **kwargs) -> List[Dict[str, Any]]:
        """初始化账单数据"""
        pass

    @classmethod
    @abstractmethod
    def identifier(cls, first_line: str) -> bool:
        """判断是否为当前策略的账单类型"""
        pass

    # @classmethod
    # def identifier(cls, first_line: str) -> bool:
    #     """判断是否为当前策略的账单类型"""
    #     pass

    # @abstractmethod
    # def get_uuid(self, data: Dict) -> str:
    #     """获取唯一标识符"""
    #     pass

    # @abstractmethod
    # def get_status(self, data: Dict) -> str:
    #     """获取交易状态"""
    #     pass

    # @abstractmethod
    # def get_note(self, data: Dict) -> str:
    #     """获取备注信息"""
    #     pass

    # @abstractmethod
    # def get_amount(self, data: Dict) -> str:
    #     """获取金额"""
    #     pass

    # @abstractmethod
    # def get_tag(self, data: Dict) -> str:
    #     """获取标签"""
    #     pass

    # @abstractmethod
    # def get_balance(self, data: Dict) -> str:
    #     """获取余额"""
    #     pass

    # @abstractmethod
    # def get_commission(self, data: Dict) -> str:
    #     """获取手续费"""
    #     pass

    # @abstractmethod
    # def get_installment_granularity(self, data: Dict) -> str:
    #     """获取分期粒度"""
    #     pass

    # @abstractmethod
    # def get_installment_cycle(self, data: Dict) -> int:
    #     """获取分期周期"""
    #     pass

    # @abstractmethod
    # def get_discount(self, data: Dict) -> bool:
    #     """获取折扣信息"""
    #     pass

    # @abstractmethod
    # def should_ignore(self, data: Dict) -> bool:
    #     """判断是否应忽略该行"""
    #     pass
