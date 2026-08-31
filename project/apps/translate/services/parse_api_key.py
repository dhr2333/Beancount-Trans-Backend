"""账单云端解析只用用户在 Copilot 填写的密钥，不回退平台 Key。"""


def resolve_parse_deepseek_api_key(config) -> str:
    return (getattr(config, 'assistant_api_key', None) or '').strip()
