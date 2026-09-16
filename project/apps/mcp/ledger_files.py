"""用户账本文件的只读访问与路径约束。"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User

from project.utils.file import BeanFileManager

BEAN_SUFFIX = '.bean'


class LedgerFileError(RuntimeError):
    """账本文件不可读：路径越界、类型不符、超限或不存在。"""


@dataclass(frozen=True)
class LedgerFile:
    path: str
    size_bytes: int
    content: str


def user_assets_root(user: User) -> Path:
    return Path(BeanFileManager.get_user_assets_path(user)).resolve()


def resolve_ledger_file(user: User, path: str) -> Path:
    """把相对路径解析为用户账本目录内的 .bean 文件绝对路径。"""
    raw = (path or '').strip()
    if not raw:
        raise LedgerFileError('path 不能为空')

    root = user_assets_root(user)
    candidate = Path(raw)
    full = (candidate if candidate.is_absolute() else root / candidate).resolve()
    if full != root and root not in full.parents:
        raise LedgerFileError(f'只允许读取自己账本目录内的文件：{raw}')
    if full.suffix.lower() != BEAN_SUFFIX:
        raise LedgerFileError(f'只允许读取 {BEAN_SUFFIX} 后缀的账本文件：{raw}')
    if not full.is_file():
        raise LedgerFileError(f'文件不存在：{raw}')

    max_bytes = int(getattr(settings, 'MCP_MAX_FILE_BYTES', 1024 * 1024))
    size = full.stat().st_size
    if size > max_bytes:
        raise LedgerFileError(f'文件过大（{size} 字节，上限 {max_bytes} 字节）：{raw}')

    return full


def read_ledger_file(user: User, path: str) -> LedgerFile:
    full = resolve_ledger_file(user, path)
    try:
        content = full.read_text(encoding='utf-8', errors='replace')
    except OSError as exc:
        raise LedgerFileError(f'读取失败：{exc}') from exc
    relative = str(full.relative_to(user_assets_root(user)))
    return LedgerFile(path=relative, size_bytes=full.stat().st_size, content=content)
