# project/apps/translate/services/init/strategies/alipay_init_strategy.py
from translate.services.init.strategies.base_bill_init_strategy import InitStrategy


class WeChatPayInitStrategy(InitStrategy):
    """微信账单初始化策略"""
    
    def init(self):
        pass
    
    @classmethod
    def identifier(cls, first_line: str) -> bool:
        """判断是否为支付宝账单"""
        pass
