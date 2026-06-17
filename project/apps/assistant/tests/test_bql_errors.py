from beanquery.compiler import CompilationError

from project.apps.assistant.services.bql_errors import format_bql_error


class TestFormatBqlError:
    def test_greater_amount_int_hint(self):
        exc = CompilationError('operator "greater(amount, int)" not supported')
        msg = format_bql_error(exc)
        assert 'number > N' in msg
        assert 'units(position)' in msg

    def test_generic_compilation_error(self):
        exc = CompilationError('syntax error near FROM')
        msg = format_bql_error(exc)
        assert '查询失败' in msg
        assert 'BQL 能力说明' in msg

    def test_generic_exception(self):
        msg = format_bql_error(RuntimeError('unexpected'))
        assert '查询失败: unexpected' in msg
