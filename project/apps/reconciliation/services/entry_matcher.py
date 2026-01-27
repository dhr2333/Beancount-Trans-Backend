"""
条目匹配服务

用于匹配 Beancount 条目，支持格式差异的容错匹配。
"""
import logging
from decimal import Decimal
from typing import Dict, List, Tuple, Optional, Any
from datetime import date

from beancount import loader
from beancount.core.data import Transaction, Pad, Balance

logger = logging.getLogger(__name__)


class EntryMatcher:
    """Beancount 条目匹配器
    
    用于匹配 Transaction、Pad、Balance 条目，支持格式差异的容错匹配。
    """
    
    @staticmethod
    def normalize_transaction(entry: Transaction) -> Dict[str, Any]:
        """标准化 Transaction 条目，提取核心字段
        
        Args:
            entry: Beancount Transaction 条目
            
        Returns:
            标准化后的字典，包含：
            - type: 'Transaction'
            - date: 日期
            - payee: Payee（如果有）
            - narration: Narration（如果有）
            - postings: 过账列表，每个过账包含 account 和 amount/currency
        """
        postings = []
        for posting in entry.postings:
            posting_dict = {
                'account': posting.account.strip()
            }
            if posting.units:
                posting_dict['amount'] = Decimal(str(posting.units.number))
                posting_dict['currency'] = posting.units.currency
            else:
                posting_dict['amount'] = None
                posting_dict['currency'] = None
            postings.append(posting_dict)
        
        return {
            'type': 'Transaction',
            'date': entry.date,
            'payee': entry.payee if entry.payee else None,
            'narration': entry.narration if entry.narration else None,
            'postings': postings
        }
    
    @staticmethod
    def normalize_pad(entry: Pad) -> Dict[str, Any]:
        """标准化 Pad 条目
        
        Args:
            entry: Beancount Pad 条目
            
        Returns:
            标准化后的字典，包含：
            - type: 'Pad'
            - date: 日期
            - account: 账户
            - source_account: 源账户
        """
        return {
            'type': 'Pad',
            'date': entry.date,
            'account': entry.account.strip(),
            'source_account': entry.source_account.strip()
        }
    
    @staticmethod
    def normalize_balance(entry: Balance) -> Dict[str, Any]:
        """标准化 Balance 条目
        
        Args:
            entry: Beancount Balance 条目
            
        Returns:
            标准化后的字典，包含：
            - type: 'Balance'
            - date: 日期
            - account: 账户
            - amount: 金额
            - currency: 币种
        """
        amount = None
        currency = None
        if entry.amount:
            amount = Decimal(str(entry.amount.number))
            currency = entry.amount.currency
        
        return {
            'type': 'Balance',
            'date': entry.date,
            'account': entry.account.strip(),
            'amount': amount,
            'currency': currency
        }
    
    @staticmethod
    def normalize_entry(entry: Any) -> Optional[Dict[str, Any]]:
        """标准化条目（去除格式差异）
        
        Args:
            entry: Beancount 条目（Transaction、Pad 或 Balance）
            
        Returns:
            标准化后的字典，如果条目类型不支持则返回 None
        """
        if isinstance(entry, Transaction):
            return EntryMatcher.normalize_transaction(entry)
        elif isinstance(entry, Pad):
            return EntryMatcher.normalize_pad(entry)
        elif isinstance(entry, Balance):
            return EntryMatcher.normalize_balance(entry)
        else:
            return None
    
    @staticmethod
    def match_transaction(entry1: Dict, entry2: Dict) -> bool:
        """匹配两个 Transaction 条目
        
        匹配规则：
        - 日期必须相同
        - Payee 必须相同（如果都存在）
        - Narration 可以不同（允许格式差异）
        - 过账必须匹配（账户、金额、币种）
        
        Args:
            entry1: 第一个标准化 Transaction 条目
            entry2: 第二个标准化 Transaction 条目
            
        Returns:
            是否匹配
        """
        # 检查日期
        if entry1['date'] != entry2['date']:
            return False
        
        # 检查 Payee（如果都存在）
        if entry1['payee'] and entry2['payee']:
            if entry1['payee'] != entry2['payee']:
                return False
        elif entry1['payee'] or entry2['payee']:
            # 一个存在一个不存在，不匹配
            return False
        
        # 检查过账数量
        if len(entry1['postings']) != len(entry2['postings']):
            return False
        
        # 匹配过账（允许顺序不同）
        postings1 = sorted(entry1['postings'], key=lambda p: (p['account'], p.get('amount') or 0, p.get('currency') or ''))
        postings2 = sorted(entry2['postings'], key=lambda p: (p['account'], p.get('amount') or 0, p.get('currency') or ''))
        
        for p1, p2 in zip(postings1, postings2):
            if p1['account'] != p2['account']:
                return False
            if p1.get('amount') is not None and p2.get('amount') is not None:
                if p1['amount'] != p2['amount']:
                    return False
            elif p1.get('amount') != p2.get('amount'):
                return False
            if p1.get('currency') != p2.get('currency'):
                return False
        
        return True
    
    @staticmethod
    def match_pad(entry1: Dict, entry2: Dict) -> bool:
        """匹配两个 Pad 条目
        
        匹配规则：
        - 日期必须相同
        - 账户必须相同
        - 源账户必须相同
        
        Args:
            entry1: 第一个标准化 Pad 条目
            entry2: 第二个标准化 Pad 条目
            
        Returns:
            是否匹配
        """
        return (
            entry1['date'] == entry2['date'] and
            entry1['account'] == entry2['account'] and
            entry1['source_account'] == entry2['source_account']
        )
    
    @staticmethod
    def match_balance(entry1: Dict, entry2: Dict) -> bool:
        """匹配两个 Balance 条目
        
        匹配规则：
        - 日期必须相同
        - 账户必须相同
        - 金额必须相同（允许格式差异，如 1000.00 vs 1000）
        - 币种必须相同
        
        Args:
            entry1: 第一个标准化 Balance 条目
            entry2: 第二个标准化 Balance 条目
            
        Returns:
            是否匹配
        """
        return (
            entry1['date'] == entry2['date'] and
            entry1['account'] == entry2['account'] and
            entry1['amount'] == entry2['amount'] and
            entry1['currency'] == entry2['currency']
        )
    
    @staticmethod
    def match_entries(entry1: Dict, entry2: Dict) -> bool:
        """匹配两个条目
        
        Args:
            entry1: 第一个标准化条目
            entry2: 第二个标准化条目
            
        Returns:
            是否匹配
        """
        if entry1['type'] != entry2['type']:
            return False
        
        if entry1['type'] == 'Transaction':
            return EntryMatcher.match_transaction(entry1, entry2)
        elif entry1['type'] == 'Pad':
            return EntryMatcher.match_pad(entry1, entry2)
        elif entry1['type'] == 'Balance':
            return EntryMatcher.match_balance(entry1, entry2)
        else:
            return False
    
    @staticmethod
    def match_entry_lists(entries1: List[Dict], entries2: List[Dict]) -> List[Tuple[Dict, Dict]]:
        """匹配两组条目，返回匹配对列表
        
        Args:
            entries1: 第一组标准化条目
            entries2: 第二组标准化条目
            
        Returns:
            匹配对列表，每个元素是 (entry1, entry2) 元组
        """
        matched_pairs = []
        used_indices = set()
        
        for entry1 in entries1:
            for idx, entry2 in enumerate(entries2):
                if idx in used_indices:
                    continue
                if EntryMatcher.match_entries(entry1, entry2):
                    matched_pairs.append((entry1, entry2))
                    used_indices.add(idx)
                    break
        
        return matched_pairs
    
    @staticmethod
    def parse_bean_file(file_path: str) -> List[Dict[str, Any]]:
        """解析 Beancount 文件，提取 Transaction、Pad、Balance 条目
        
        Args:
            file_path: .bean 文件路径
            
        Returns:
            标准化条目列表
        """
        try:
            entries, errors, options = loader.load_file(file_path)
            
            # 记录解析错误（但不阻止处理）
            if errors:
                logger.warning(f"解析文件 {file_path} 时有 {len(errors)} 个错误")
                for error in errors[:3]:  # 只记录前3个错误
                    logger.warning(f"  - {error}")
            
            normalized_entries = []
            for entry in entries:
                normalized = EntryMatcher.normalize_entry(entry)
                if normalized:
                    # 保存原始条目引用（用于后续行号映射）
                    normalized['_original_entry'] = entry
                    normalized_entries.append(normalized)
            
            return normalized_entries
            
        except Exception as e:
            logger.error(f"解析文件失败 {file_path}: {e}")
            return []


