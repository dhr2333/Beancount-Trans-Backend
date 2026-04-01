"""自托管静态多 Fava 实例：解析 FAVA_STATIC_USER_MAP 并按用户解析入口 URL。"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def parse_fava_static_user_map(raw: str) -> dict[str, str]:
    """
    支持：
    - JSON 对象：{"alice":"http://host:5001","bob":"http://host:5002"}
    - 逗号分隔：alice=http://host:5001,bob=http://host:5002
    """
    raw = (raw or "").strip()
    if not raw:
        return {}
    if raw.startswith("{"):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            logger.warning("FAVA_STATIC_USER_MAP JSON 解析失败: %s", e)
            return {}
        if not isinstance(data, dict):
            return {}
        return {str(k).strip(): str(v).strip().rstrip("/") for k, v in data.items() if k and v}
    out: dict[str, str] = {}
    for part in raw.split(","):
        part = part.strip()
        if not part or "=" not in part:
            continue
        key, val = part.split("=", 1)
        key, val = key.strip(), val.strip().rstrip("/")
        if key and val:
            out[key] = val
    return out


def resolve_static_fava_url(user: Any, mapping: dict[str, str]) -> str | None:
    """
    按映射表解析当前用户对应的 Fava 根 URL（浏览器可访问，通常为宿主机:端口）。
    查找顺序：Git repo_name（若存在）→ username → Assets 子目录 basename。
    """
    if not mapping:
        return None

    from django.core.exceptions import ObjectDoesNotExist

    from project.utils.file import BeanFileManager

    candidates: list[str] = []
    try:
        repo = user.git_repo
        if repo and getattr(repo, "repo_name", None):
            candidates.append(repo.repo_name)
    except (ObjectDoesNotExist, AttributeError):
        pass

    if getattr(user, "username", None):
        candidates.append(user.username)

    try:
        bn = os.path.basename(BeanFileManager.get_user_assets_path(user))
        if bn and bn not in candidates:
            candidates.append(bn)
    except Exception:
        pass

    for key in candidates:
        if key and key in mapping:
            return mapping[key]
    return None
