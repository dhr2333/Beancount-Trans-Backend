"""测试 Copilot 填写的密钥：未填写时 Copilot 可走平台，云端解析不可用。"""
from dataclasses import dataclass

from django.conf import settings
from openai import AuthenticationError, OpenAI

from .api_key_resolver import (
    DEFAULT_ASSISTANT_BASE_URL,
    DEFAULT_ASSISTANT_MODEL,
    _is_deepseek_base_url,
)

EMPTY_WITH_PLATFORM = (
    '未填写用户密钥。Copilot 可使用平台密钥聊天；云端解析不可用。'
)
EMPTY_WITHOUT_PLATFORM = (
    '未填写密钥，且未配置平台密钥。Copilot 与云端解析均不可用。'
)
EMPTY_LOCAL = (
    '未填写密钥。本地 Copilot 可连接；云端解析需要填写 DeepSeek 密钥。'
)
SUCCESS = '密钥有效。Copilot 与云端解析均可使用。'


@dataclass(frozen=True)
class KeyTestResult:
    ok: bool
    copilot_available: bool
    parse_available: bool
    detail: str


def probe_llm_connection(api_key: str, base_url: str, model: str) -> None:
    client = OpenAI(
        api_key=api_key,
        base_url=base_url.rstrip('/'),
        timeout=8.0,
    )
    try:
        client.chat.completions.create(
            model=model,
            messages=[{'role': 'user', 'content': 'ping'}],
            max_tokens=1,
            temperature=0,
        )
    except AuthenticationError as exc:
        raise ValueError('密钥无效') from exc


def evaluate_assistant_key(*, api_key: str, base_url: str, model: str) -> KeyTestResult:
    user_key = (api_key or '').strip()
    resolved_base = (base_url or '').strip() or DEFAULT_ASSISTANT_BASE_URL
    resolved_model = (model or '').strip() or DEFAULT_ASSISTANT_MODEL

    if not user_key:
        if _is_deepseek_base_url(resolved_base):
            platform_key = (getattr(settings, 'ASSISTANT_DEEPSEEK_API_KEY', None) or '').strip()
            if platform_key:
                return KeyTestResult(
                    ok=True,
                    copilot_available=True,
                    parse_available=False,
                    detail=EMPTY_WITH_PLATFORM,
                )
            return KeyTestResult(
                ok=False,
                copilot_available=False,
                parse_available=False,
                detail=EMPTY_WITHOUT_PLATFORM,
            )
        return KeyTestResult(
            ok=True,
            copilot_available=True,
            parse_available=False,
            detail=EMPTY_LOCAL,
        )

    try:
        probe_llm_connection(user_key, resolved_base, resolved_model)
    except Exception as exc:
        return KeyTestResult(
            ok=False,
            copilot_available=False,
            parse_available=False,
            detail=f'密钥测试失败：{exc}',
        )

    return KeyTestResult(
        ok=True,
        copilot_available=True,
        parse_available=True,
        detail=SUCCESS,
    )
