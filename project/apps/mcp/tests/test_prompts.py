"""MCP Prompts 的注册信息与内容测试。"""
import asyncio

import pytest

pytestmark = pytest.mark.django_db(transaction=True)

EXPECTED_PROMPTS = {'insight_review', 'monthly_review'}


def _get(server, name, arguments=None):
    return asyncio.run(server.get_prompt(name, arguments))


@pytest.fixture
def prompts(mcp_server):
    return {prompt.name: prompt for prompt in asyncio.run(mcp_server.list_prompts())}


class TestPromptRegistration:
    def test_registers_expected_prompts(self, prompts):
        assert set(prompts) == EXPECTED_PROMPTS

    def test_every_prompt_has_description(self, prompts):
        for prompt in prompts.values():
            assert prompt.description

    def test_period_argument_is_optional(self, prompts):
        for prompt in prompts.values():
            arguments = {argument.name: argument for argument in prompt.arguments}
            assert set(arguments) == {'period'}
            assert arguments['period'].required is False


class TestPromptContent:
    def test_insight_review_default_period(self, mcp_server):
        result = _get(mcp_server, 'insight_review')
        text = result.messages[0].content.text
        assert '最近 3 个月' in text
        assert 'run_bql' in text

    def test_insight_review_custom_period(self, mcp_server):
        result = _get(mcp_server, 'insight_review', {'period': '2026 年 1 月'})
        assert '2026 年 1 月' in result.messages[0].content.text

    def test_monthly_review_mentions_output_structure(self, mcp_server):
        text = _get(mcp_server, 'monthly_review').messages[0].content.text
        assert '月度复盘' in text
        assert '结余' in text

    def test_unknown_prompt(self, mcp_server):
        with pytest.raises(Exception):
            _get(mcp_server, 'no_such_prompt')
