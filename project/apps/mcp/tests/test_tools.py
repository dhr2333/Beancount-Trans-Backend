"""MCP Tools 的注册信息与调用行为测试。"""
import asyncio

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from .conftest import SAMPLE_BEAN

pytestmark = pytest.mark.django_db(transaction=True)

EXPECTED_TOOLS = {'get_ledger_context', 'run_bql', 'read_ledger_file'}


def _call(server, name, arguments):
    return asyncio.run(server.call_tool(name, arguments))


@pytest.fixture
def tools(mcp_server):
    return {tool.name: tool for tool in asyncio.run(mcp_server.list_tools())}


class TestToolRegistration:
    def test_registers_expected_tools(self, tools):
        assert set(tools) == EXPECTED_TOOLS

    def test_every_tool_has_description_and_schema(self, tools):
        for tool in tools.values():
            assert tool.description
            assert tool.input_schema['type'] == 'object'

    def test_tool_arguments(self, tools):
        assert 'query' in tools['run_bql'].input_schema['properties']
        assert 'path' in tools['read_ledger_file'].input_schema['properties']
        assert tools['get_ledger_context'].input_schema['properties'] == {}


class TestGetLedgerContext:
    def test_returns_context_text(self, mcp_server, ledger_files):
        result = asyncio.run(mcp_server.call_tool('get_ledger_context', {}))
        assert result.is_error is not True
        text = result.content[0].text
        assert '基准日期' in text
        assert 'Expenses:Food' in text

    def test_includes_platform_catalog(self, mcp_server, ledger_files, platform_metadata):
        result = asyncio.run(mcp_server.call_tool('get_ledger_context', {}))
        assert '餐饮' in result.content[0].text


class TestRunBql:
    def test_returns_structured_result(self, mcp_server, ledger_files):
        result = asyncio.run(
            mcp_server.call_tool(
                'run_bql',
                {'query': "SELECT account, sum(position) WHERE account ~ 'Expenses' GROUP BY account"},
            )
        )
        payload = result.structured_content
        assert payload['row_count'] >= 1
        assert payload['truncated'] is False
        assert 'Expenses:Food' in payload['result_text']
        assert payload['bql'].startswith('SELECT')

    def test_enriches_with_platform_description(self, mcp_server, ledger_files, platform_metadata):
        result = asyncio.run(
            mcp_server.call_tool(
                'run_bql',
                {'query': "SELECT account, sum(position) WHERE account ~ 'Expenses' GROUP BY account"},
            )
        )
        assert '餐饮（Expenses:Food）' in result.structured_content['result_text']

    def test_rejects_write_statement(self, mcp_server, ledger_files):
        with pytest.raises(ToolError, match='BQL 校验失败'):
            _call(mcp_server, 'run_bql', {'query': 'INSERT INTO foo VALUES (1)'})

    def test_rejects_units_position_comparison(self, mcp_server, ledger_files):
        with pytest.raises(ToolError, match='BQL 校验失败'):
            _call(
                mcp_server,
                'run_bql',
                {'query': "SELECT date WHERE account ~ 'Expenses' AND units(position) > 100"},
            )

    def test_missing_ledger_reports_tool_error(self, mcp_server, settings, monkeypatch, tmp_path):
        monkeypatch.setattr(settings, 'ASSETS_BASE_PATH', tmp_path / 'nonexistent')
        with pytest.raises(ToolError, match='账本不可用'):
            _call(mcp_server, 'run_bql', {'query': 'SELECT account'})

    def test_isolated_between_users(self, mcp_server, ledger_files, other_user, other_assets, settings, monkeypatch):
        monkeypatch.setattr(settings, 'MCP_DEV_USERNAME', other_user.username)
        result = asyncio.run(
            mcp_server.call_tool(
                'run_bql',
                {'query': "SELECT account, sum(position) WHERE account ~ 'Expenses' GROUP BY account"},
            )
        )
        assert 'Expenses:Rent' in result.structured_content['result_text']
        assert 'Expenses:Food' not in result.structured_content['result_text']


class TestReadLedgerFile:
    def test_reads_main_bean(self, mcp_server, ledger_files):
        result = asyncio.run(mcp_server.call_tool('read_ledger_file', {'path': 'main.bean'}))
        payload = result.structured_content
        assert payload['path'] == 'main.bean'
        assert payload['content'] == SAMPLE_BEAN
        assert payload['size_bytes'] == len(SAMPLE_BEAN.encode('utf-8'))

    def test_blocks_path_traversal(self, mcp_server, ledger_files):
        with pytest.raises(ToolError, match='只允许读取自己账本目录内的文件'):
            _call(mcp_server, 'read_ledger_file', {'path': '../outside.bean'})

    def test_rejects_non_bean_file(self, mcp_server, ledger_files):
        with pytest.raises(ToolError, match='后缀'):
            _call(mcp_server, 'read_ledger_file', {'path': 'notes.txt'})

    def test_rejects_missing_file(self, mcp_server, ledger_files):
        with pytest.raises(ToolError, match='文件不存在'):
            _call(mcp_server, 'read_ledger_file', {'path': 'nope.bean'})


class TestErrors:
    def test_unknown_tool(self, mcp_server):
        with pytest.raises(ToolError):
            _call(mcp_server, 'no_such_tool', {})

    def test_missing_identity(self, mcp_server, settings, monkeypatch):
        monkeypatch.setattr(settings, 'MCP_DEV_USERNAME', '')
        with pytest.raises(ToolError, match='未提供访问令牌'):
            _call(mcp_server, 'get_ledger_context', {})
