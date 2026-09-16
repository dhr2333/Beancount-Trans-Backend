"""MCP Resources：把账本上下文以可挂载资源形式暴露给 MCP 客户端。"""
from __future__ import annotations

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ResourceError

from project.apps.assistant.services.bql_reference import build_bql_capability_reference
from project.apps.assistant.services.metadata_catalog import load_account_catalog, load_tag_catalog

from .identity import IdentityError, get_current_user
from .ledger_files import LedgerFileError, read_ledger_file

ACCOUNTS_URI = 'ledger://accounts'
TAGS_URI = 'ledger://tags'
BQL_REFERENCE_URI = 'ledger://bql-reference'
MAIN_BEAN_URI = 'ledger://main.bean'

ACCOUNTS_DESCRIPTION = '平台账户目录（账户路径 → 描述），用于把用户的类别说法映射到 BQL 的 account 条件'
TAGS_DESCRIPTION = '平台标签目录（完整标签路径 → 描述），用于 BQL 的 \'路径\' IN tags 条件'
BQL_REFERENCE_DESCRIPTION = 'beanquery 实际支持的 BQL 语法说明、推荐写法与常见失败原因'
MAIN_BEAN_DESCRIPTION = '当前用户账本入口文件 main.bean 的原文，可据此了解 include 结构'


def _current_user():
    try:
        return get_current_user()
    except IdentityError as exc:
        raise ResourceError(str(exc)) from exc


def register(server: MCPServer) -> None:
    @server.resource(
        ACCOUNTS_URI,
        name='accounts',
        title='平台账户目录',
        description=ACCOUNTS_DESCRIPTION,
        mime_type='text/plain',
    )
    def accounts_resource() -> str:
        entries = load_account_catalog(_current_user())
        lines = ['平台账户目录（账户路径 → 描述）:']
        if entries:
            lines.extend(f'  {entry.account} → {entry.description or "（无描述）"}' for entry in entries)
        else:
            lines.append('  （暂无已启用账户）')
        return '\n'.join(lines)

    @server.resource(
        TAGS_URI,
        name='tags',
        title='平台标签目录',
        description=TAGS_DESCRIPTION,
        mime_type='text/plain',
    )
    def tags_resource() -> str:
        entries = load_tag_catalog(_current_user())
        lines = ['平台标签目录（完整标签路径 → 描述）:']
        if entries:
            lines.extend(f'  {entry.full_path} → {entry.description or "（无描述）"}' for entry in entries)
        else:
            lines.append('  （暂无已启用标签）')
        return '\n'.join(lines)

    @server.resource(
        BQL_REFERENCE_URI,
        name='bql_reference',
        title='BQL 语法参考',
        description=BQL_REFERENCE_DESCRIPTION,
        mime_type='text/plain',
    )
    def bql_reference_resource() -> str:
        return build_bql_capability_reference(insight_mode=True)

    @server.resource(
        MAIN_BEAN_URI,
        name='main_bean',
        title='账本入口文件',
        description=MAIN_BEAN_DESCRIPTION,
        mime_type='text/x-beancount',
    )
    def main_bean_resource() -> str:
        try:
            return read_ledger_file(_current_user(), 'main.bean').content
        except LedgerFileError as exc:
            raise ResourceError(str(exc)) from exc
