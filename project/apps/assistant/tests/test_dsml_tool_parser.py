from project.apps.assistant.services.dsml_tool_parser import (
    extract_dsml_tool_calls,
    strip_dsml_markup,
)

_DSML_BQL_HALF = (
    '<|DSML|tool_calls>\n'
    '<|DSML|invoke name="run_bql">\n'
    '<|DSML|parameter name="query" string="true">'
    "SELECT sum(units(position)) WHERE account ~ '^Expenses:Food' AND year = 2026 AND month = 5"
    '<|DSML|parameter>\n'
    '<|DSML|invoke>\n'
    '<|DSML|tool_calls>'
)

_DSML_BQL_FULLWIDTH = (
    '<｜｜DSML｜｜tool_calls>\n'
    '<｜｜DSML｜｜invoke name="run_bql">\n'
    '<｜｜DSML｜｜parameter name="query" string="true">'
    "SELECT sum(units(position)) WHERE account ~ '^Expenses:Food' AND year = 2026 AND month = 5"
    '<｜｜DSML｜｜parameter>\n'
    '<｜｜DSML｜｜invoke>\n'
    '<｜｜DSML｜｜tool_calls>'
)


class TestStripDsmlMarkup:
    def test_strips_halfwidth_dsml(self):
        text = f'前缀说明\n{_DSML_BQL_HALF}\n后缀'
        assert strip_dsml_markup(text) == '前缀说明\n\n后缀'

    def test_strips_fullwidth_dsml(self):
        assert 'DSML' not in strip_dsml_markup(_DSML_BQL_FULLWIDTH)

    def test_passthrough_without_dsml(self):
        text = '5月餐饮支出为 **0** 元。'
        assert strip_dsml_markup(text) == text

    def test_empty_input(self):
        assert strip_dsml_markup('') == ''


class TestExtractDsmlToolCalls:
    def test_extracts_run_bql_halfwidth(self):
        calls = extract_dsml_tool_calls(_DSML_BQL_HALF)
        assert len(calls) == 1
        assert calls[0].name == 'run_bql'
        assert 'Expenses:Food' in calls[0].arguments
        assert calls[0].id.startswith('dsml_')

    def test_extracts_run_bql_fullwidth(self):
        calls = extract_dsml_tool_calls(_DSML_BQL_FULLWIDTH)
        assert len(calls) == 1
        assert calls[0].name == 'run_bql'
        assert 'month = 5' in calls[0].arguments

    def test_extracts_get_ledger_context(self):
        text = (
            '<|DSML|invoke name="get_ledger_context">\n'
            '<|DSML|invoke>'
        )
        calls = extract_dsml_tool_calls(text)
        assert len(calls) == 1
        assert calls[0].name == 'get_ledger_context'
        assert calls[0].arguments == '{}'

    def test_returns_empty_without_dsml(self):
        assert extract_dsml_tool_calls('普通回答') == []

    def test_ignores_invoke_without_query(self):
        text = '<|DSML|invoke name="run_bql">\n<|DSML|invoke>'
        assert extract_dsml_tool_calls(text) == []

    def test_dsml_with_surrounding_text(self):
        text = f'我来查一下。\n{_DSML_BQL_HALF}'
        calls = extract_dsml_tool_calls(text)
        assert len(calls) == 1
        cleaned = strip_dsml_markup(text)
        assert '我来查一下' in cleaned
        assert 'DSML' not in cleaned
