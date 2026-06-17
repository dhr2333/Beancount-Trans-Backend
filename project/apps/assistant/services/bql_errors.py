"""将 beanquery 编译/执行错误格式化为 LLM 可理解的提示。"""


def format_bql_error(exc: Exception) -> str:
    """将 BQL 异常转为带修复建议的文本。"""
    message = str(exc)

    if 'greater(amount, int)' in message or 'less(amount, int)' in message:
        return (
            '查询失败: BQL 不支持在 WHERE 中比较 units(position) 或 position 与数字。'
            '请改用 number > N（支出）或 number < -N（收入），'
            '或使用 ORDER BY units(position) DESC LIMIT N 后由你在回答中筛选大额交易。'
        )

    if 'CompilationError' in type(exc).__name__ or 'compilation' in message.lower():
        return (
            f'查询失败: {message}。'
            '请参考 BQL 能力说明：简化 WHERE 条件，避免在 WHERE 使用聚合函数或 HAVING。'
        )

    return f'查询失败: {message}'
