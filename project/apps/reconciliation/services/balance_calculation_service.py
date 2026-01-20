# Beancount-Trans-Backend/project/apps/reconciliation/services/balance_calculation_service.py
"""
余额计算服务

使用 Beancount 核心库加载账本并计算指定账户的余额。
"""
import logging
import os
from decimal import Decimal
from datetime import date
from typing import Optional, Dict

from beancount import loader
from beancount.core import realization

from project.utils.file import BeanFileManager

logger = logging.getLogger(__name__)


class BalanceCalculationService:
    """余额计算服务
    
    使用 Beancount 核心库加载账本并计算指定账户的余额。
    """
    
    @staticmethod
    def calculate_balance(
        user, 
        account_name: str, 
        as_of_date: Optional[date] = None
    ) -> Dict[str, Decimal]:
        """计算账户所有币种的余额
        
        Args:
            user: 用户对象
            account_name: 账户路径，如 "Assets:Bank:CMB"
            as_of_date: 截止日期，默认为 None（计算到最新）
            
        Returns:
            账户所有币种余额的字典，格式：{currency: Decimal(amount)}
            如果账户不存在或余额为空，返回空字典 {}
            
        Raises:
            ValueError: 账本加载失败（有严重错误）
        """
        # 1. 获取用户 main.bean 文件路径
        main_bean_path = BeanFileManager.get_main_bean_path(user)
        
        # 检查文件是否存在
        if not os.path.exists(main_bean_path):
            logger.warning(f"账本文件不存在: {main_bean_path}")
            return {}
        
        # 2. 加载账本
        try:
            entries, errors, options = loader.load_file(main_bean_path)
        except Exception as e:
            logger.error(f"加载账本文件失败: {main_bean_path}, 错误: {e}")
            raise ValueError(f"加载账本文件失败: {e}")
        
        # 3. 检查加载错误
        if errors:
            # 记录警告，但不阻止计算（beancount 允许部分错误）
            logger.warning(f"账本加载有警告: {len(errors)} 个错误")
            for error in errors[:5]:  # 只记录前5个错误
                logger.warning(f"  - {error}")
        
        # 4. 如果指定了日期，过滤条目
        if as_of_date:
            filtered_entries = []
            for entry in entries:
                # 只保留日期小于等于 as_of_date 的条目
                if hasattr(entry, 'date') and entry.date <= as_of_date:
                    filtered_entries.append(entry)
            entries = filtered_entries
        
        # 5. 构建账户树并获取余额
        try:
            real_account = realization.realize(entries)
            account_real = realization.get(real_account, account_name)
        except Exception as e:
            logger.error(f"构建账户树失败: {e}")
            raise ValueError(f"构建账户树失败: {e}")
        
        # 6. 如果账户不存在，返回空字典
        if account_real is None:
            logger.debug(f"账户不存在: {account_name}")
            return {}
        
        # 7. 获取所有币种余额
        balance = account_real.balance
        if balance.is_empty():
            logger.debug(f"账户 {account_name} 余额为空")
            return {}
        
        # 遍历余额 Inventory，提取所有币种及其余额
        # balance 是一个 Inventory 对象，包含 Position 对象列表
        balances = {}
        
        for position in balance:
            if position.units:
                currency = position.units.currency
                amount = position.units.number
                
                if amount is not None:
                    balances[currency] = Decimal(str(amount))
                else:
                    # 币种存在但金额为 None，记录为 0.00
                    logger.debug(f"账户 {account_name} 币种 {currency} 余额为 None，记录为 0.00")
                    balances[currency] = Decimal('0.00')
        
        if balances:
            logger.debug(f"账户 {account_name} 余额: {balances}")
        else:
            logger.debug(f"账户 {account_name} 没有有效余额")
        
        return balances
    
    @staticmethod
    def generate_balance_directive(
        account_name: str, 
        balance: Decimal, 
        balance_date: date
    ) -> str:
        """生成 balance 指令
        
        注意：balance_date 应该是明日，表示该日期开始时的余额
        
        Args:
            account_name: 账户路径，如 "Assets:Bank:CMB"
            balance: 余额（Decimal 类型）
            balance_date: 余额日期（应为明日）
            
        Returns:
            balance 指令字符串，格式："{balance_date} balance {account_name} {balance} CNY"
            
        示例:
            "2026-01-21 balance Assets:Bank:CMB 1005.00 CNY"
        """
        return f"{balance_date} balance {account_name} {balance} CNY"
    
    @staticmethod
    def generate_pad_directive(
        account_name: str, 
        pad_account: str, 
        pad_date: date
    ) -> str:
        """生成 pad 指令
        
        注意：pad_date 应该是今日，在 balance 之前
        
        Args:
            account_name: 需要 pad 的账户路径，如 "Assets:Bank:CMB"
            pad_account: pad 目标账户，如 "Expenses:Adjustment"
            pad_date: pad 日期（应为今日）
            
        Returns:
            pad 指令字符串，格式："{pad_date} pad {account_name} {pad_account}"
            
        示例:
            "2026-01-20 pad Assets:Bank:CMB Expenses:Adjustment"
        """
        return f"{pad_date} pad {account_name} {pad_account}"

