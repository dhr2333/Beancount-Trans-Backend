"""MCP Resources 的注册信息与读取行为测试。"""
import asyncio

import pytest

from project.apps.mcp.resources import (
    ACCOUNTS_URI,
    BQL_REFERENCE_URI,
    MAIN_BEAN_URI,
    TAGS_URI,
)

from .conftest import SAMPLE_BEAN

pytestmark = pytest.mark.django_db(transaction=True)

EXPECTED_URIS = {ACCOUNTS_URI, TAGS_URI, BQL_REFERENCE_URI, MAIN_BEAN_URI}


def _read(server, uri):
    contents = asyncio.run(server.read_resource(uri))
    return contents[0].content


@pytest.fixture
def resources(mcp_server):
    return {str(resource.uri): resource for resource in asyncio.run(mcp_server.list_resources())}


class TestResourceRegistration:
    def test_registers_expected_resources(self, resources):
        assert set(resources) == EXPECTED_URIS

    def test_every_resource_has_description_and_mime_type(self, resources):
        for resource in resources.values():
            assert resource.description
            assert resource.mime_type


class TestResourceContent:
    def test_accounts_catalog(self, mcp_server, ledger_files, platform_metadata):
        text = _read(mcp_server, ACCOUNTS_URI)
        assert 'Expenses:Food' in text
        assert '餐饮' in text

    def test_accounts_catalog_without_metadata(self, mcp_server, ledger_files):
        assert '暂无已启用账户' in _read(mcp_server, ACCOUNTS_URI)

    def test_tags_catalog(self, mcp_server, ledger_files, platform_metadata):
        text = _read(mcp_server, TAGS_URI)
        assert 'Discretionary' in text
        assert '非必要支出' in text

    def test_bql_reference(self, mcp_server, ledger_files):
        text = _read(mcp_server, BQL_REFERENCE_URI)
        assert 'sum(units(position))' in text

    def test_main_bean(self, mcp_server, ledger_files):
        assert _read(mcp_server, MAIN_BEAN_URI) == SAMPLE_BEAN

    def test_main_bean_missing(self, mcp_server, tmp_path, settings, monkeypatch):
        monkeypatch.setattr(settings, 'ASSETS_BASE_PATH', tmp_path / 'nonexistent')
        with pytest.raises(Exception, match='文件不存在'):
            _read(mcp_server, MAIN_BEAN_URI)

    def test_unknown_uri(self, mcp_server, ledger_files):
        with pytest.raises(Exception):
            _read(mcp_server, 'ledger://unknown')
