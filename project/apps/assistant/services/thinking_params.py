"""DeepSeek 消费端 DeepThink：单模型 + thinking 请求参数。"""
from typing import Any

from .api_key_resolver import LlmProvider


def is_thinking_enabled(provider: LlmProvider, *, deep_think: bool) -> bool:
    return deep_think and provider.supports_thinking_param


def build_completion_extras(provider: LlmProvider, *, deep_think: bool) -> dict[str, Any]:
    if not is_thinking_enabled(provider, deep_think=deep_think):
        return {}
    return {'extra_body': {'thinking': {'type': 'enabled'}}}
