# project/apps/translate/utils/beancount_validator.py
"""
Beancount 语法校验工具

使用 beancount 库验证 Beancount 条目的语法正确性
"""
import logging
from typing import Tuple, List, Optional
from beancount import loader
from beancount.core import data
from beancount.ops import validation
from beancount.parser import booking, parser

logger = logging.getLogger(__name__)


class BeancountValidator:
    """Beancount 语法校验器"""

    @staticmethod
    def _check_balance_errors(entries, options_map) -> List[str]:
        """对已解析条目做 booking 与交易平衡校验，返回金额相关错误信息。

        - booking.book 会自动补全「另一条过账行金额留空」的场景，空金额不算错误；
        - 只收集 booking 错误与交易平衡错误，不引入未知账户等无关 validation。
        """
        try:
            booked_entries, booking_errors = booking.book(entries, options_map)
        except Exception as e:
            logger.error("Beancount 金额校验异常: %s", str(e), exc_info=True)
            return [f"金额校验异常: {str(e)}"]

        messages: List[str] = []
        for error in booking_errors:
            messages.append(getattr(error, "message", str(error)))

        try:
            balance_errors = validation.validate_check_transaction_balances(
                booked_entries, options_map
            )
        except Exception as e:
            logger.error("Beancount 交易平衡校验异常: %s", str(e), exc_info=True)
            messages.append(f"金额校验异常: {str(e)}")
        else:
            for error in balance_errors:
                messages.append(getattr(error, "message", str(error)))

        # 去重并保持出现顺序
        return list(dict.fromkeys(messages))

    @staticmethod
    def validate_entries(
        entries_text: str, check_balance: bool = False
    ) -> Tuple[bool, Optional[str], List[str]]:
        """验证 Beancount 条目的语法（可选金额平衡）

        Args:
            entries_text: Beancount 条目文本（可以是多条，用换行分隔）
            check_balance: 是否额外校验交易金额平衡；默认仅校验语法

        Returns:
            (is_valid, error_message, errors):
            - is_valid: 是否有效
            - error_message: 错误信息（如果有）
            - errors: 详细错误列表
        """
        if not entries_text or not entries_text.strip():
            return True, None, []

        try:
            # 使用 beancount 解析器解析条目
            entries, errors, options_map = parser.parse_string(entries_text)

            if errors:
                # 提取错误信息
                error_messages = []
                for error in errors:
                    if hasattr(error, 'message'):
                        error_messages.append(str(error.message))
                    else:
                        error_messages.append(str(error))

                error_summary = '; '.join(error_messages[:3])  # 最多显示前3个错误
                if len(error_messages) > 3:
                    error_summary += f' ... (共 {len(error_messages)} 个错误)'

                return False, error_summary, error_messages

            # 语法通过后，按需校验金额平衡
            if check_balance:
                balance_messages = BeancountValidator._check_balance_errors(
                    entries, options_map
                )
                if balance_messages:
                    error_summary = '金额校验未通过: ' + '; '.join(balance_messages[:3])
                    if len(balance_messages) > 3:
                        error_summary += f' ... (共 {len(balance_messages)} 个错误)'
                    return False, error_summary, balance_messages

            return True, None, []

        except Exception as e:
            error_msg = f"Beancount 语法校验异常: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg, [error_msg]
    
    @staticmethod
    def validate_single_entry(
        entry_text: str, check_balance: bool = False
    ) -> Tuple[bool, Optional[str]]:
        """验证单个 Beancount 条目

        Args:
            entry_text: 单个 Beancount 条目文本
            check_balance: 是否额外校验交易金额平衡

        Returns:
            (is_valid, error_message)
        """
        is_valid, error_message, _ = BeancountValidator.validate_entries(
            entry_text, check_balance=check_balance
        )
        return is_valid, error_message
    
    @staticmethod
    def validate_multiple_entries(
        entries_list: List[str], check_balance: bool = False
    ) -> Tuple[bool, Optional[str], List[Tuple[int, str]]]:
        """验证多个 Beancount 条目

        Args:
            entries_list: Beancount 条目列表
            check_balance: 是否额外校验交易金额平衡

        Returns:
            (is_valid, error_message, error_entries):
            - is_valid: 是否全部有效
            - error_message: 错误信息摘要
            - error_entries: 有错误的条目列表 [(index, error_message), ...]
        """
        if not entries_list:
            return True, None, []
        
        # 合并所有条目进行验证
        combined_text = '\n'.join(entries_list)
        is_valid, error_message, errors = BeancountValidator.validate_entries(
            combined_text, check_balance=check_balance
        )
        
        # 如果整体验证失败，尝试逐个验证以定位具体错误条目
        error_entries = []
        if not is_valid:
            for idx, entry in enumerate(entries_list):
                entry_valid, entry_error = BeancountValidator.validate_single_entry(
                    entry, check_balance=check_balance
                )
                if not entry_valid:
                    error_entries.append((idx, entry_error))
        
        return is_valid, error_message, error_entries
