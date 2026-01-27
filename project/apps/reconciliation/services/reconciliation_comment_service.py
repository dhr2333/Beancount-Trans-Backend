"""
对账注释管理服务

用于检测和注释对账条目，避免与 Git 仓库中的记录重复。
"""
import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from beancount import loader
from beancount.core.data import Transaction, Pad, Balance

from project.utils.file import BeanFileManager
from .entry_matcher import EntryMatcher

logger = logging.getLogger(__name__)


class ReconciliationCommentService:
    """对账注释管理服务
    
    负责检测 trans/reconciliation.bean 与 Git 仓库数据的重复条目，
    并注释匹配的条目以避免数据重复。
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
            
            # 检查文件名是否匹配（处理相对路径）
            if filename and lineno:
                # 标准化路径进行比较
                abs_filename = os.path.abspath(filename)
                abs_file_path = os.path.abspath(file_path)
                
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
            
            for entry in entries:
                # 只处理 Transaction、Pad、Balance
                if not isinstance(entry, (Transaction, Pad, Balance)):
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
    def _parse_git_repository_entries(user) -> List[Dict]:
        """解析 Git 仓库数据中的对账条目
        
        Git 仓库数据已拉取到服务器本地用户目录，不包含 trans/ 目录。
        
        Args:
            user: 用户对象
            
        Returns:
            标准化条目列表
        """
        user_assets_path = Path(BeanFileManager.get_user_assets_path(user))
        
        if not user_assets_path.exists():
            logger.debug(f"用户目录不存在: {user_assets_path}")
            return []
        
        all_entries = []
        parsed_files = []
        skipped_files = []
        
        # 遍历用户目录中的所有 .bean 文件（排除 trans/ 目录）
        for bean_file in user_assets_path.rglob('*.bean'):
            # 排除 trans/ 目录
            relative_path = bean_file.relative_to(user_assets_path)
            if 'trans' in relative_path.parts:
                skipped_files.append(str(bean_file))
                continue
            
            try:
                entries = EntryMatcher.parse_bean_file(str(bean_file))
                
                # 过滤掉来自 trans/ 目录的条目（因为 main.bean 可能包含 trans/reconciliation.bean）
                filtered_entries = []
                for entry in entries:
                    original_entry = entry.get('_original_entry')
                    if original_entry and hasattr(original_entry, 'meta') and original_entry.meta:
                        filename = original_entry.meta.get('filename')
                        if filename:
                            # 检查文件名是否包含 trans/ 目录
                            abs_filename = os.path.abspath(filename)
                            abs_user_path = os.path.abspath(user_assets_path)
                            if abs_filename.startswith(os.path.join(abs_user_path, 'trans')):
                                continue
                    filtered_entries.append(entry)
                
                all_entries.extend(filtered_entries)
                parsed_files.append({'file': str(bean_file), 'entry_count': len(filtered_entries)})
                logger.debug(f"从 {bean_file} 解析了 {len(filtered_entries)} 个条目（过滤了 {len(entries) - len(filtered_entries)} 个来自 trans/ 的条目）")
            except Exception as e:
                logger.warning(f"解析文件失败 {bean_file}: {e}")
        
        return all_entries
    
    @staticmethod
    def detect_duplicate_entries(user) -> Dict[str, Any]:
        """仅检测重复条目，不执行注释（用于前端展示）
        
        检测逻辑：
        - 比较 Git 仓库数据（已拉取到服务器本地）与 trans/reconciliation.bean 的条目
        - Git 仓库中不包含 trans/ 目录（因为被忽略）
        
        Args:
            user: 用户对象
            
        Returns:
            {
                'has_duplicates': True/False,
                'duplicate_count': 5,
                'duplicates': [
                    {
                        'type': 'Transaction',
                        'date': '2026-01-24',
                        'account': 'Assets:Savings:Web:WechatFund',
                        'line_numbers': [70, 71, 72]
                    }
                ]
            }
        """
        # 解析平台文件
        platform_entries, entry_to_lines = ReconciliationCommentService._parse_reconciliation_bean(user)
        
        # 解析 Git 仓库数据
        git_entries = ReconciliationCommentService._parse_git_repository_entries(user)
        
        # 匹配重复条目
        matched_pairs = EntryMatcher.match_entry_lists(platform_entries, git_entries)
        
        duplicates = []
        for platform_entry, git_entry in matched_pairs:
            # 找到 platform_entry 在 platform_entries 中的索引
            try:
                entry_index = platform_entries.index(platform_entry)
                line_numbers = entry_to_lines.get(entry_index, [])
            except ValueError:
                # 如果找不到索引（理论上不应该发生），跳过
                logger.warning("无法找到条目索引，跳过")
                continue
                
            # 格式化日期
            entry_date = platform_entry['date']
            if hasattr(entry_date, 'isoformat'):
                date_str = entry_date.isoformat()
            elif isinstance(entry_date, str):
                date_str = entry_date
            else:
                date_str = str(entry_date)
            
            duplicates.append({
                'type': platform_entry['type'],
                'date': date_str,
                'account': platform_entry.get('account', ''),
                'line_numbers': line_numbers
            })
        
        return {
            'has_duplicates': len(duplicates) > 0,
            'duplicate_count': len(duplicates),
            'duplicates': duplicates
        }
    
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
    
    @staticmethod
    def _uncomment_lines_in_file(file_path: str) -> int:
        """取消文件中所有对账条目的注释
        
        只取消以 "Beancount-Trans" "对账调整" 开头的 Transaction 的注释，
        以及相关的 Pad 和 Balance 条目的注释。
        只处理 "; "（分号+空格）格式的注释。
        
        Args:
            file_path: 文件路径
            
        Returns:
            实际取消注释的行数
        """
        if not os.path.exists(file_path):
            logger.warning(f"文件不存在: {file_path}")
            return 0
        
        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        uncommented_count = 0
        in_reconciliation_transaction = False  # 标记是否在 Transaction 的 posting 行中
        
        # 取消注释（移除行首的 ;）
        for idx, line in enumerate(lines):
            stripped = line.lstrip()
            original_indent = len(line) - len(line.lstrip())
            
            # 检查是否是 Transaction 的日期行（可能被注释）
            if stripped.startswith('; '):
                # 从原始行移除 "; "，保留所有后续内容（包括缩进和换行符）
                content_after_comment = line[2:]
                content_stripped = content_after_comment.lstrip()  # 用于检查内容
                
                # 检查是否是 Transaction 日期行（包含日期和 "Beancount-Trans"）
                if '"Beancount-Trans"' in content_stripped and ('*' in content_stripped or '!' in content_stripped):
                    # 这是 Transaction 的日期行，取消注释
                    # content_after_comment 已经包含了正确的缩进和内容
                    lines[idx] = content_after_comment
                    uncommented_count += 1
                    in_reconciliation_transaction = True
                    continue
                
                # 检查是否是 Pad 或 Balance 指令
                if 'balance' in content_stripped.lower() or 'pad' in content_stripped.lower():
                    # 保留原有缩进，移除注释符号
                    lines[idx] = content_after_comment
                    uncommented_count += 1
                    # pad/balance 行标志着 Transaction 的结束，重置状态
                    in_reconciliation_transaction = False
                    continue
                
                # 如果当前在 Transaction 的 posting 行中，且这行被注释了，取消注释
                if in_reconciliation_transaction:
                    # 检查是否是 posting 行
                    # posting 行的特征：分号后的内容有缩进（通常是4个或更多空格）
                    content_indent = len(content_after_comment) - len(content_after_comment.lstrip())
                    
                    # posting 行通常有4个或更多空格的缩进（在分号后）
                    if content_indent >= 4:
                        # 保留分号后的缩进结构，移除注释符号
                        lines[idx] = content_after_comment
                        uncommented_count += 1
                        continue
            
            # 检查是否是 Transaction 的 posting 行（未注释的）
            elif in_reconciliation_transaction:
                # 检查是否是 posting 行（有缩进）
                original_indent = len(line) - len(line.lstrip())
                if original_indent >= 4 and line.strip():
                    # 这是 posting 行，继续
                    continue
                else:
                    # 遇到空行或下一个条目，重置标记
                    in_reconciliation_transaction = False
            
            # 检查是否是未注释的 Transaction 日期行
            if not stripped.startswith(';') and ('*' in stripped or '!' in stripped):
                if '"Beancount-Trans"' in stripped:
                    in_reconciliation_transaction = True
                else:
                    in_reconciliation_transaction = False
        
        # 写回文件
        if uncommented_count > 0:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            logger.info(f"已取消 {uncommented_count} 行的注释在文件 {file_path}")
        
        return uncommented_count
    
    @staticmethod
    def detect_and_comment_duplicates(user) -> Dict[str, Any]:
        """检测并自动注释重复条目（Git同步时调用）
        
        流程：
        1. 解析 trans/reconciliation.bean 中的所有对账条目（平台管理）
        2. 解析 Git 仓库数据中的所有 .bean 文件的对账条目
           - Git 仓库数据已拉取到服务器本地用户目录
           - Git 仓库中不包含 trans/ 目录（因为被 .gitignore 忽略）
           - 遍历用户目录中除 trans/ 外的所有 .bean 文件
        3. 匹配重复条目
        4. 自动注释 trans/reconciliation.bean 中匹配的条目
        5. 返回注释结果
        
        Args:
            user: 用户对象
            
        Returns:
            {
                'commented_count': 5,
                'matched_entries': [...],
                'message': '已注释 5 个重复条目'
            }
        """
        # 解析平台文件
        platform_entries, entry_to_lines = ReconciliationCommentService._parse_reconciliation_bean(user)
        
        if not platform_entries:
            logger.debug("平台对账文件为空，无需检测")
            return {
                'commented_count': 0,
                'matched_entries': [],
                'message': '没有对账条目需要检测'
            }
        
        # 解析 Git 仓库数据
        git_entries = ReconciliationCommentService._parse_git_repository_entries(user)
        
        if not git_entries:
            logger.debug("Git 仓库中没有对账条目")
            return {
                'commented_count': 0,
                'matched_entries': [],
                'message': 'Git 仓库中没有对账条目'
            }
        
        # 匹配重复条目
        matched_pairs = EntryMatcher.match_entry_lists(platform_entries, git_entries)
        
        if not matched_pairs:
            logger.debug("未发现重复条目")
            return {
                'commented_count': 0,
                'matched_entries': [],
                'message': '未发现重复条目'
            }
        
        # 收集所有需要注释的行号
        all_line_numbers = []
        matched_entry_info = []
        
        for platform_entry, git_entry in matched_pairs:
            # 找到 platform_entry 在 platform_entries 中的索引
            try:
                entry_index = platform_entries.index(platform_entry)
                line_numbers = entry_to_lines.get(entry_index, [])
            except ValueError:
                # 如果找不到索引（理论上不应该发生），跳过
                logger.warning("无法找到条目索引，跳过")
                continue
                
            if line_numbers:
                all_line_numbers.extend(line_numbers)
                # 格式化日期
                entry_date = platform_entry['date']
                if hasattr(entry_date, 'isoformat'):
                    date_str = entry_date.isoformat()
                elif isinstance(entry_date, str):
                    date_str = entry_date
                else:
                    date_str = str(entry_date)
                
                matched_entry_info.append({
                    'type': platform_entry['type'],
                    'date': date_str,
                    'account': platform_entry.get('account', ''),
                    'line_numbers': line_numbers
                })
        
        # 去重行号
        unique_line_numbers = sorted(set(all_line_numbers))
        
        # 注释文件
        reconciliation_path = BeanFileManager.get_reconciliation_bean_path(user)
        commented_count = ReconciliationCommentService._comment_lines_in_file(
            reconciliation_path, unique_line_numbers
        )
        
        return {
            'commented_count': commented_count,
            'matched_entries': matched_entry_info,
            'message': f'已注释 {commented_count} 个重复条目'
        }
    
    @staticmethod
    def uncomment_all_entries(user) -> int:
        """取消所有对账条目的注释，返回取消注释数量（删除Git仓库时调用）
        
        Args:
            user: 用户对象
            
        Returns:
            取消注释的行数
        """
        reconciliation_path = BeanFileManager.get_reconciliation_bean_path(user)
        return ReconciliationCommentService._uncomment_lines_in_file(reconciliation_path)

