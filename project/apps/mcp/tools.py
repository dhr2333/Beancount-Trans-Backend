"""MCP Tools：把平台已具备的账本只读能力暴露给 MCP 客户端。

工具实现全部复用 assistant 应用下的服务层，不重复实现 BQL 校验与账本解析。
"""
from __future__ import annotations

import logging

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import BaseModel, Field

from project.apps.assistant.services.bql_validator import BQLValidationError
from project.apps.assistant.services.ledger_query import LedgerNotFoundError, LedgerQueryService
from project.apps.assistant.services.schema_provider import get_ledger_context

from .identity import IdentityError, get_current_user
from .ledger_files import LedgerFileError, read_ledger_file

logger = logging.getLogger(__name__)

GET_LEDGER_CONTEXT_DESCRIPTION = (
    '获取用户账本上下文：平台账户/标签目录（含描述）、'
    '账本实际账户、默认货币、BQL 语法说明与查询示例。'
    '执行 BQL 查询前应先调用本工具了解可用的账户与标签。'
)

RUN_BQL_DESCRIPTION = (
    '执行只读 BQL 查询并返回表格结果。必须 SELECT 开头；'
    '分析/余额/合计/对比类问题必须用 sum(units(position)) 与 GROUP BY 聚合，禁止拉明细后心算；'
    '用户说的类别名称先对照平台账户/标签目录映射到 account ~ / \'标签路径\' IN tags；'
    '账户用 account ~ 正则；时间用 year/month 或 date 范围；'
    '金额过滤用 number > N，禁止 units(position) > N；'
    '类目总额用前缀 account ~ 的 sum，子科目拆分用 GROUP BY（父/子账户金额独立）；'
    '结果截断时改用 GROUP BY 重查；'
    '解读 Income/Liabilities 结果时注意复式记账符号，向用户展示收入/欠款用绝对值。'
)


class BqlQueryResult(BaseModel):
    """BQL 查询结果。"""

    bql: str = Field(description='实际执行的 BQL 语句')
    result_text: str = Field(description='表格形式的查询结果')
    row_count: int = Field(description='符合条件的总行数（未截断前的行数）')
    truncated: bool = Field(description='结果是否因超出上限被截断')


READ_LEDGER_FILE_DESCRIPTION = (
    '读取当前用户账本目录内的单个 .bean 文件原文。'
    'path 为相对账本根目录的路径（如 main.bean、2026/01/xxx.bean），'
    '用于查看账户结构、include 关系与原始交易记录；'
    '需要统计或筛选时请改用 run_bql，不要靠读取文件人工汇总。'
)


class LedgerFileContent(BaseModel):
    """账本文件内容。"""

    path: str = Field(description='相对账本根目录的路径')
    size_bytes: int = Field(description='文件大小（字节）')
    content: str = Field(description='文件原文')


def _current_user():
    try:
        return get_current_user()
    except IdentityError as exc:
        raise ToolError(str(exc)) from exc


def register(server: MCPServer) -> None:
    """把账本查询相关工具注册到 MCP 服务。"""

    @server.tool(name='get_ledger_context', description=GET_LEDGER_CONTEXT_DESCRIPTION)
    def get_ledger_context_tool() -> str:
        return get_ledger_context(_current_user())

    @server.tool(name='run_bql', description=RUN_BQL_DESCRIPTION)
    def run_bql_tool(query: str) -> BqlQueryResult:
        service = LedgerQueryService(_current_user())
        try:
            result = service.execute(query)
        except BQLValidationError as exc:
            raise ToolError(f'BQL 校验失败：{exc}') from exc
        except LedgerNotFoundError as exc:
            raise ToolError(f'账本不可用：{exc}') from exc
        except ValueError as exc:
            raise ToolError(f'BQL 执行失败：{exc}') from exc
        return BqlQueryResult(
            bql=result.bql,
            result_text=result.result_text,
            row_count=result.row_count,
            truncated=result.truncated,
        )

    @server.tool(name='read_ledger_file', description=READ_LEDGER_FILE_DESCRIPTION)
    def read_ledger_file_tool(path: str) -> LedgerFileContent:
        try:
            ledger_file = read_ledger_file(_current_user(), path)
        except LedgerFileError as exc:
            raise ToolError(str(exc)) from exc
        return LedgerFileContent(
            path=ledger_file.path,
            size_bytes=ledger_file.size_bytes,
            content=ledger_file.content,
        )
