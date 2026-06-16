"""解析 DeepSeek API Key：优先用户配置，回退平台 Key。"""
from dataclasses import dataclass
from typing import Literal, Optional

from django.conf import settings
from django.contrib.auth.models import User

from project.apps.translate.models import FormatConfig


ApiKeySource = Literal['user', 'platform', 'none']


@dataclass(frozen=True)
class ResolvedApiKey:
    api_key: Optional[str]
    source: ApiKeySource


def resolve_api_key(user: User) -> ResolvedApiKey:
    """优先用户 FormatConfig.deepseek_apikey，其次平台 ASSISTANT_DEEPSEEK_API_KEY。"""
    config = FormatConfig.get_user_config(user)
    user_key = (config.deepseek_apikey or '').strip()
    if user_key:
        return ResolvedApiKey(api_key=user_key, source='user')

    platform_key = (getattr(settings, 'ASSISTANT_DEEPSEEK_API_KEY', None) or '').strip()
    if platform_key:
        return ResolvedApiKey(api_key=platform_key, source='platform')

    return ResolvedApiKey(api_key=None, source='none')
