# project/apps/translate/utils/beancount_validator.py
"""
Beancount 语法校验工具

使用 beancount 库验证 Beancount 条目的语法正确性
"""
import logging
from typing import Tuple, List, Optional
from beancount import loader
from beancount.core import data
from beancount.parser import parser

logger = logging.getLogger(__name__)


class BeancountValidator:
    """Beancount 语法校验器"""
    
    @staticmethod
    def validate_entries(entries_text: str) -> Tuple[bool, Optional[str], List[str]]:
        """验证 Beancount 条目的语法
        
        Args:
            entries_text: Beancount 条目文本（可以是多条，用换行分隔）
            
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
            
            return True, None, []
            
        except Exception as e:
            error_msg = f"Beancount 语法校验异常: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg, [error_msg]
    
    @staticmethod
    def validate_single_entry(entry_text: str) -> Tuple[bool, Optional[str]]:
        """验证单个 Beancount 条目
        
        Args:
            entry_text: 单个 Beancount 条目文本
            
        Returns:
            (is_valid, error_message)
        """
        is_valid, error_message, _ = BeancountValidator.validate_entries(entry_text)
        return is_valid, error_message
    
    @staticmethod
    def validate_multiple_entries(entries_list: List[str]) -> Tuple[bool, Optional[str], List[Tuple[int, str]]]:
        """验证多个 Beancount 条目
        
        Args:
            entries_list: Beancount 条目列表
            
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
        is_valid, error_message, errors = BeancountValidator.validate_entries(combined_text)
        
        # 如果整体验证失败，尝试逐个验证以定位具体错误条目
        error_entries = []
        if not is_valid:
            for idx, entry in enumerate(entries_list):
                entry_valid, entry_error = BeancountValidator.validate_single_entry(entry)
                if not entry_valid:
                    error_entries.append((idx, entry_error))
        
        return is_valid, error_message, error_entries
