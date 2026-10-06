"""
对账注释管理服务

用于解析 trans/reconciliation.bean 条目，并支持注释指定行。
"""
import logging
import os
import re
from typing import Dict, List, Optional, Any, Tuple

from beancount import loader
from beancount.core.data import Transaction, Pad, Balance

from project.utils.file import BeanFileManager
from .entry_matcher import EntryMatcher

logger = logging.getLogger(__name__)


class ReconciliationCommentService:
    """对账注释管理服务

    负责解析 trans/reconciliation.bean 中的对账条目，
    并支持注释指定行（供撤销对账使用）。
    """
    
    @staticmethod
    def _is_entry_commented(entry: Any, file_path: str, original_file_lines: List[str] = None) -> bool:
        """检查条目是否已被注释
        
        Args:
            entry: Beancount 条目
            file_path: 文件路径
            original_file_lines: 文件的原始内容（如果为None，则重新读取文件）
            
        Returns:
            如果条目已被注释返回 True，否则返回 False
        """
        # Beancount 条目有 meta 属性，包含 filename 和 lineno
        if hasattr(entry, 'meta') and entry.meta:
            filename = entry.meta.get('filename')
            lineno = entry.meta.get('lineno')
            
            # 检查文件名是否匹配（处理相对路径）
            if filename and lineno:
                # 标准化路径进行比较
                abs_filename = os.path.abspath(filename)
                abs_file_path = os.path.abspath(file_path)
                
                if abs_filename == abs_file_path:
                    # 使用原始文件内容（如果提供），否则重新读取文件
                    try:
                        if original_file_lines is None:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                lines = f.readlines()
                        else:
                            lines = original_file_lines
                        
                        # 检查从 lineno 开始的前几行，看是否有注释
                        # Beancount 解析器可能会跳过注释行，所以我们需要检查多个可能的位置
                        start_line = lineno - 1  # 转换为0-based索引
                        
                        # Beancount 解析器在解析时可能会跳过注释行，返回的 lineno 指向去注释后的内容位置
                        # 我们需要向前查找，找到实际的注释行
                        # 检查从 start_line 开始向前最多10行，找到第一个包含日期格式的注释行
                        for check_line_idx in range(start_line, max(-1, start_line - 10), -1):
                            if check_line_idx < 0 or check_line_idx >= len(lines):
                                continue
                            
                            check_line = lines[check_line_idx]
                            check_stripped = check_line.lstrip()
                            
                            # 跳过空行
                            if not check_stripped or check_stripped == '\n':
                                continue
                            
                            # 检查是否是条目的开始行（包含日期格式 YYYY-MM-DD）
                            date_pattern = r'\d{4}-\d{2}-\d{2}'
                            if re.search(date_pattern, check_stripped):
                                # 如果这一行被注释了，条目就被注释了
                                if check_stripped.startswith(';'):
                                    return True
                                else:
                                    # 如果这一行未被注释，且是条目的开始行，则条目未被注释
                                    return False
                        
                        # 如果没有找到明确的条目行，默认认为未被注释（保守策略）
                        return False
                    except Exception as e:
                        logger.warning(f"读取文件检查注释状态失败 {file_path}: {e}")
        
        return False
    
    @staticmethod
    def _get_entry_line_numbers(entry: Any, file_path: str) -> List[int]:
        """获取条目在文件中的行号列表
        
        Beancount 条目可能跨多行，返回所有相关行的行号。
        通过读取文件内容来确定条目的实际行号范围。
        
        Args:
            entry: Beancount 条目
            file_path: 文件路径
            
        Returns:
            行号列表（从1开始）
        """
        line_numbers = []
        
        # Beancount 条目有 meta 属性，包含 filename 和 lineno
        if hasattr(entry, 'meta') and entry.meta:
            filename = entry.meta.get('filename')
            lineno = entry.meta.get('lineno')
            
            # 检查文件名是否匹配（处理相对路径、符号链接）
            if filename and lineno:
                # 标准化路径进行比较
                abs_filename = os.path.abspath(os.path.realpath(filename))
                abs_file_path = os.path.abspath(os.path.realpath(file_path))
                
                if abs_filename == abs_file_path:
                    # 读取文件内容，确定条目的实际行数
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            lines = f.readlines()
                        
                        # Transaction 条目可能跨多行
                        if isinstance(entry, Transaction):
                            # 从 lineno 开始，找到所有相关的行
                            # Transaction 格式：
                            # YYYY-MM-DD * "Payee" "Narration"
                            #     Account1 Amount Currency
                            #     Account2 Amount Currency
                            start_line = lineno - 1  # 转换为0-based索引
                            if start_line < len(lines):
                                line_numbers.append(lineno)  # 日期行
                                # 查找后续的 posting 行（以空格开头）
                                for i in range(start_line + 1, len(lines)):
                                    line = lines[i]
                                    # Posting 行通常以4个空格开头
                                    if line.strip() and (line.startswith('    ') or line.startswith('\t')):
                                        line_numbers.append(i + 1)  # 转换为1-based
                                    elif line.strip() and not line.strip().startswith(';'):
                                        # 遇到非空行且不是注释，可能是下一个条目
                                        break
                        elif isinstance(entry, (Pad, Balance)):
                            # Pad 和 Balance 通常只占一行
                            line_numbers.append(lineno)
                    except Exception as e:
                        logger.warning(f"读取文件确定行号失败 {file_path}: {e}")
                        # 降级：只返回起始行号
                        line_numbers.append(lineno)
        
        return line_numbers
    
    @staticmethod
    def _parse_reconciliation_bean(user) -> Tuple[List[Dict], Dict[int, List[int]]]:
        """解析 trans/reconciliation.bean 文件
        
        Args:
            user: 用户对象
            
        Returns:
            (标准化条目列表, 索引到行号的映射字典)
        """
        reconciliation_path = BeanFileManager.get_reconciliation_bean_path(user)
        
        if not os.path.exists(reconciliation_path):
            logger.debug(f"对账文件不存在: {reconciliation_path}")
            return [], {}
        
        try:
            # 在解析之前，先读取文件的原始内容
            # 这样我们可以在检查注释时使用原始内容
            with open(reconciliation_path, 'r', encoding='utf-8') as f:
                original_file_lines = f.readlines()
            
            entries, errors, options = loader.load_file(reconciliation_path)
            
            if errors:
                logger.warning(f"解析对账文件时有 {len(errors)} 个错误")
            
            normalized_entries = []
            entry_to_lines = {}
            
            abs_reconciliation_path = os.path.abspath(os.path.realpath(reconciliation_path))
            for entry in entries:
                # 只处理 Transaction、Pad、Balance
                if not isinstance(entry, (Transaction, Pad, Balance)):
                    continue
                # 只处理来自 reconciliation.bean 的条目（避免 include 导致路径不一致时遗漏行号）
                if hasattr(entry, 'meta') and entry.meta:
                    entry_filename = entry.meta.get('filename')
                    if entry_filename and os.path.abspath(os.path.realpath(entry_filename)) != abs_reconciliation_path:
                        continue
                
                # 跳过已注释的条目（使用原始文件内容）
                if ReconciliationCommentService._is_entry_commented(entry, reconciliation_path, original_file_lines):
                    continue
                
                normalized = EntryMatcher.normalize_entry(entry)
                if normalized:
                    normalized['_original_entry'] = entry
                    normalized_entries.append(normalized)
                    
                    # 获取行号，使用索引作为键
                    line_numbers = ReconciliationCommentService._get_entry_line_numbers(
                        entry, reconciliation_path
                    )
                    if line_numbers:
                        # 使用 normalized_entries 中的索引作为键
                        entry_index = len(normalized_entries) - 1
                        entry_to_lines[entry_index] = line_numbers
            
            return normalized_entries, entry_to_lines
            
        except Exception as e:
            logger.error(f"解析对账文件失败 {reconciliation_path}: {e}")
            return [], {}
    
    @staticmethod
    def _comment_lines_in_file(file_path: str, line_numbers: List[int]) -> int:
        """注释文件中的指定行
        
        Args:
            file_path: 文件路径
            line_numbers: 要注释的行号列表（从1开始）
            
        Returns:
            实际注释的行数
        """
        if not os.path.exists(file_path):
            logger.warning(f"文件不存在: {file_path}")
            return 0
        
        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        commented_count = 0
        line_numbers_set = set(line_numbers)
        
        # 注释指定行（如果还没有被注释）
        for idx, line in enumerate(lines):
            line_num = idx + 1  # 转换为从1开始的行号
            if line_num in line_numbers_set:
                # 检查是否已经被注释
                stripped = line.lstrip()
                if stripped and not stripped.startswith(';'):
                    # 在行的最前面添加注释符号 "; "（分号+空格），保留原有缩进和内容
                    lines[idx] = '; ' + line
                    commented_count += 1
        
        # 写回文件
        if commented_count > 0:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            logger.info(f"已注释 {commented_count} 行在文件 {file_path}")
        
        return commented_count
