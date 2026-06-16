"""封装 beanquery 对用户账本的只读查询。"""
import io
import logging
import os
from dataclasses import dataclass
from typing import Optional

import beanquery
from beanquery.query_render import render_text
from django.conf import settings
from django.contrib.auth.models import User

from project.utils.file import BeanFileManager

from .bql_validator import BQLValidationError, validate_bql

logger = logging.getLogger(__name__)


class LedgerNotFoundError(FileNotFoundError):
    """用户账本文件不存在。"""


@dataclass
class BQLQueryResult:
    bql: str
    result_text: str
    row_count: int
    truncated: bool


class LedgerQueryService:
    """对用户 main.bean 执行 BQL 查询。"""

    def __init__(self, user: User):
        self.user = user
        self.ledger_path = BeanFileManager.get_main_bean_path(user)
        self.max_rows = int(getattr(settings, 'ASSISTANT_MAX_BQL_ROWS', 100))

    def ledger_exists(self) -> bool:
        return os.path.isfile(self.ledger_path)

    def _connect(self):
        if not self.ledger_exists():
            raise LedgerNotFoundError(f'账本文件不存在: {self.ledger_path}')
        conn = beanquery.connect(None)
        conn.attach(f'beancount:{self.ledger_path}')
        return conn

    def execute(self, query: str) -> BQLQueryResult:
        bql = validate_bql(query)
        conn = self._connect()
        try:
            cursor = conn.execute(bql)
            rows = cursor.fetchall()
            row_count = len(rows)
            truncated = row_count > self.max_rows
            if truncated:
                rows = rows[:self.max_rows]

            out = io.StringIO()
            dcontext = conn.options.get('dcontext')
            render_text(cursor.description, rows, dcontext, out)
            result_text = out.getvalue()
            if truncated:
                result_text += f'\n... (结果已截断，仅显示前 {self.max_rows} 行，共 {row_count} 行)'
            return BQLQueryResult(
                bql=bql,
                result_text=result_text or '(无结果)',
                row_count=row_count,
                truncated=truncated,
            )
        except BQLValidationError:
            raise
        except Exception as exc:
            logger.exception('BQL 执行失败: %s', bql)
            raise ValueError(f'BQL 执行失败: {exc}') from exc

    def list_accounts(self, limit: int = 200) -> list[str]:
        """获取账本中的账户列表。"""
        if not self.ledger_exists():
            return []
        try:
            result = self.execute(
                f'SELECT DISTINCT account ORDER BY account LIMIT {int(limit)}'
            )
            accounts = []
            for line in result.result_text.splitlines():
                line = line.strip()
                if line and not line.startswith('account') and not set(line) <= {'-', ' '}:
                    accounts.append(line.split()[0])
            return accounts
        except Exception:
            logger.exception('获取账户列表失败')
            return []
