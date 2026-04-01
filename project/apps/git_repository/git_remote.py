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
