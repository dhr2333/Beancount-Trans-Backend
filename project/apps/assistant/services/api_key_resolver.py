"""解析账本助手 LLM 供给：用户 Provider 与平台回退。"""
from dataclasses import dataclass
from typing import Literal, Optional
from urllib.parse import urlparse

from django.conf import settings
from django.contrib.auth.models import User

from project.apps.translate.models import FormatConfig

ApiKeySource = Literal['user', 'platform', 'none']

DEFAULT_ASSISTANT_BASE_URL = 'https://api.deepseek.com'
DEFAULT_ASSISTANT_MODEL = 'deepseek-v4-flash'
OLLAMA_PLACEHOLDER_KEY = 'ollama'


@dataclass(frozen=True)
class LlmProvider:
    base_url: str
    api_key: str
    model: str
    supports_thinking_param: bool
    source: ApiKeySource

    @property
    def configured(self) -> bool:
        return self.source != 'none'


@dataclass(frozen=True)
class ResolvedApiKey:
    """兼容旧调用方，仅保留 api_key / source。"""

    api_key: Optional[str]
    source: ApiKeySource


def _default_assistant_model() -> str:
    return getattr(settings, 'ASSISTANT_MODEL', DEFAULT_ASSISTANT_MODEL)


def _default_assistant_base_url() -> str:
    return getattr(settings, 'ASSISTANT_BASE_URL', DEFAULT_ASSISTANT_BASE_URL)


def _is_deepseek_base_url(base_url: str) -> bool:
    host = (urlparse(base_url).netloc or '').lower()
    return host.endswith('deepseek.com')


def _user_assistant_configured(config: FormatConfig) -> bool:
    return bool((config.assistant_api_key or '').strip()) or bool(
        (config.assistant_base_url or '').strip()
    )


def _resolve_user_api_key(config: FormatConfig, base_url: str) -> str:
    user_key = (config.assistant_api_key or '').strip()
    if user_key:
        return user_key
    if (config.assistant_base_url or '').strip():
        return OLLAMA_PLACEHOLDER_KEY
    if _is_deepseek_base_url(base_url):
        return ''
    return OLLAMA_PLACEHOLDER_KEY


def resolve_llm_provider(user: User) -> LlmProvider:
    config = FormatConfig.get_user_config(user)

    if _user_assistant_configured(config):
        base_url = (config.assistant_base_url or '').strip() or _default_assistant_base_url()
        api_key = _resolve_user_api_key(config, base_url)
        if not api_key:
            return LlmProvider(
                base_url=base_url,
                api_key='',
                model='',
                supports_thinking_param=False,
                source='none',
            )
        model = (config.assistant_model or '').strip() or _default_assistant_model()
        return LlmProvider(
            base_url=base_url.rstrip('/'),
            api_key=api_key,
            model=model,
            supports_thinking_param=_is_deepseek_base_url(base_url),
            source='user',
        )

    platform_key = (getattr(settings, 'ASSISTANT_DEEPSEEK_API_KEY', None) or '').strip()
    if platform_key:
        base_url = _default_assistant_base_url().rstrip('/')
        return LlmProvider(
            base_url=base_url,
            api_key=platform_key,
            model=_default_assistant_model(),
            supports_thinking_param=True,
            source='platform',
        )

    return LlmProvider(
        base_url='',
        api_key='',
        model='',
        supports_thinking_param=False,
        source='none',
    )


def resolve_api_key(user: User) -> ResolvedApiKey:
    provider = resolve_llm_provider(user)
    if not provider.configured:
        return ResolvedApiKey(api_key=None, source='none')
    return ResolvedApiKey(api_key=provider.api_key, source=provider.source)
