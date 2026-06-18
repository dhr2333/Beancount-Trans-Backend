"""解析并清理 DeepSeek DSML 格式的工具调用标记。"""
import json
import re
import uuid
from dataclasses import dataclass

# 兼容半角 <|DSML| 与全角 ｜｜DSML｜｜ 变体
_DSML_TAG = r'(?:<\|DSML\||<｜｜DSML｜｜)'
_DSML_BLOCK = re.compile(
    rf'{_DSML_TAG}[^>]*>.*?(?:{_DSML_TAG}[^>]*>)',
    re.DOTALL,
)
_INVOKE_PATTERN = re.compile(
    rf'{_DSML_TAG}invoke\s+name="([^"]+)"[^>]*>(.*?)(?:{_DSML_TAG}invoke>|$)',
    re.DOTALL,
)
_PARAMETER_PATTERN = re.compile(
    rf'{_DSML_TAG}parameter\s+name="([^"]+)"[^>]*>(.*?)(?:{_DSML_TAG}parameter>|{_DSML_TAG}invoke>|$)',
    re.DOTALL,
)


@dataclass
class ParsedDsmlToolCall:
    id: str
    name: str
    arguments: str


def strip_dsml_markup(text: str) -> str:
    """移除文本中的 DSML 工具调用标记块。"""
    if not text:
        return text
    cleaned = _DSML_BLOCK.sub('', text)
    # 兜底：移除未闭合的 DSML 片段
    cleaned = re.sub(rf'{_DSML_TAG}[^>]*>.*', '', cleaned, flags=re.DOTALL)
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    return cleaned.strip()


def _parse_invoke_block(name: str, body: str) -> dict[str, str]:
    params: dict[str, str] = {}
    for match in _PARAMETER_PATTERN.finditer(body):
        param_name = match.group(1)
        param_value = match.group(2).strip()
        params[param_name] = param_value
    return params


def extract_dsml_tool_calls(text: str) -> list[ParsedDsmlToolCall]:
    """从 content 文本中提取 DSML 格式的工具调用。"""
    if not text or 'DSML' not in text:
        return []

    calls: list[ParsedDsmlToolCall] = []
    for match in _INVOKE_PATTERN.finditer(text):
        fn_name = match.group(1).strip()
        body = match.group(2)
        params = _parse_invoke_block(fn_name, body)
        if not params and fn_name == 'get_ledger_context':
            params = {}
        if fn_name == 'run_bql' and 'query' not in params:
            continue
        calls.append(ParsedDsmlToolCall(
            id=f'dsml_{uuid.uuid4().hex[:12]}',
            name=fn_name,
            arguments=json.dumps(params, ensure_ascii=False),
        ))
    return calls
