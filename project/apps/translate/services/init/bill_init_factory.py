# project/apps/translate/services/init/bill_init_factory.py
from translate.services.init.strategies.alipay_init_strategy import AlipayInitStrategy
from translate.services.init.strategies.wechat_init_strategy import WeChatPayInitStrategy
from translate.services.init.strategies.base_bill_init_strategy import InitStrategy
# from abc import ABC, abstractmethod


# class InitFactory(ABC):
#     @abstractmethod
#     def create_strategy(self) -> InitStrategy:
#         pass


# class AlipayInitFactory(InitFactory):
#     def create_strategy(self) -> InitStrategy:
#         return AlipayInitStrategy()


# class WeChatPayInitFactory(InitFactory):
#     def create_strategy(self) -> InitStrategy:
#         return WeChatPayInitStrategy()


class InitFactory:
    """账单初始化工厂类"""

    _strategies = []

    @classmethod
    def register_strategy(cls, strategy_cls):
        """注册策略类"""
        if not issubclass(strategy_cls, InitStrategy):
            raise TypeError("必须继承自InitStrategy")
        cls._strategies.append(strategy_cls)
        return strategy_cls


    @classmethod
    def create_strategy(cls, first_line: str) -> InitStrategy:
        """创建初始化策略实例"""
        for strategy in cls._strategies:
            if strategy.identifier(first_line):
                return strategy()
        raise ValueError("当前账单不支持")

    # @classmethod
    # def registered_strategies(cls) -> list:
    #     """返回已注册的策略类名称列表"""
    #     return [s.__name__ for s in cls._strategies]


InitFactory.register_strategy(AlipayInitStrategy)
