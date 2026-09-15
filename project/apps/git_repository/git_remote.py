"""从 SSH 远程 URL 推断 `owner/repo`（用于 Webhook 匹配）。"""
from __future__ import annotations

import re
from urllib.parse import urlparse


def guess_external_full_name_from_ssh(remote_ssh_url: str) -> str:
    """从常见 SSH Git URL 解析仓库路径，转为 `owner/repo` 或 `group/sub/repo` 形式。

    支持：
    - git@github.com:owner/repo.git
    - ssh://git@github.com/owner/repo.git
    - ssh://git@gitlab.com/group/sub/repo.git
    """
    if not remote_ssh_url:
        return ''
    url = remote_ssh_url.strip()

    if url.startswith('git@'):
        # git@host:path.git
        m = re.match(r'^git@[^:]+:(.+)$', url)
        if not m:
            return ''
        path = m.group(1).strip().rstrip('/')
        if path.endswith('.git'):
            path = path[:-4]
        return path

    if url.startswith('ssh://'):
        parsed = urlparse(url)
        path = (parsed.path or '').strip('/')
        if path.endswith('.git'):
            path = path[:-4]
        return path

    return ''


def parse_ssh_host(remote_ssh_url: str) -> str:
    """从 SSH Git URL 中提取主机名（不含用户名与端口）。无法解析时返回空串。"""
    url = (remote_ssh_url or '').strip()
    if not url:
        return ''
    if url.startswith('ssh://'):
        return (urlparse(url).hostname or '').lower()
    m = re.match(r'^(?:[^@/]+@)?([^:/]+):(.+)$', url)
    if not m:
        return ''
    return m.group(1).lower()


def guess_provider_from_ssh(remote_ssh_url: str) -> str:
    """根据 SSH 地址的主机名推断代码托管平台，无法识别时返回 'other'。"""
    host = parse_ssh_host(remote_ssh_url)
    if not host:
        return 'other'
    if host == 'github.com' or host.endswith('.github.com'):
        return 'github'
    if host == 'gitlab.com' or host.endswith('.gitlab.com') or 'gitlab' in host:
        return 'gitlab'
    if 'gitea' in host:
        return 'gitea'
    if 'gogs' in host:
        return 'gogs'
    return 'other'


def is_valid_ssh_git_url(remote_ssh_url: str) -> bool:
    """校验是否为受支持的 SSH Git 地址（git@host:path 或 ssh://[user@]host[:port]/path）。"""
    url = (remote_ssh_url or '').strip()
    if not url:
        return False
    if url.startswith('http://') or url.startswith('https://'):
        return False
    if url.startswith('ssh://'):
        parsed = urlparse(url)
        return bool(parsed.hostname) and bool((parsed.path or '').strip('/'))
    m = re.match(r'^(?:[^@/]+@)?([^:/]+):(.+)$', url)
    if not m:
        return False
    return bool(m.group(1)) and bool(m.group(2).strip('/'))
