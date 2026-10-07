"""
无用 pad 自动清理测试

覆盖 ReconciliationCommentService.cleanup_unused_pads：
- 真实交易使余额落入断言容差内（完全一致或相差 0.01）时，注释 reconciliation.bean 中的 pad；
- 相差超过容差（0.02）时 pad 仍被使用，不注释；
- 无 reconciliation.bean 或 pad 位于其它文件时不处理；
- 重复调用幂等。
"""
from pathlib import Path

import pytest
from django.conf import settings
from beancount import loader

from project.apps.reconciliation.services.reconciliation_comment_service import (
    ReconciliationCommentService,
)

MAIN_BEAN = (
    'option "operating_currency" "CNY"\n'
    'plugin "beancount.plugins.auto_accounts"\n'
    'include "trans/main.bean"\n'
)

PAD_LINE = '2026-10-07 pad Assets:Savings:Web:AliFund Equity:Opening-Balances'
BALANCE_LINE = '2026-10-08 balance Assets:Savings:Web:AliFund 205.76 CNY'
RECONCILIATION = f'{PAD_LINE}\n{BALANCE_LINE}\n'


def _collect_transaction(amount: str) -> str:
    return (
        '2026-10-06 * "Beancount-Trans" "解析写入"\n'
        f'    Assets:Savings:Web:AliFund {amount} CNY\n'
        f'    Income:Other -{amount} CNY\n'
    )


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


def _has_unused_pad_error(main_path: Path) -> bool:
    _entries, errors, _options = loader.load_file(str(main_path))
    return any(getattr(e, 'message', None) == 'Unused Pad entry' for e in errors)


@pytest.fixture
def build_ledger(tmp_path, monkeypatch):
    """把 ASSETS_BASE_PATH 指向临时目录，返回构建用户账本的工厂函数。"""
    base = tmp_path / 'Assets'
    base.mkdir()
    monkeypatch.setattr(settings, 'ASSETS_BASE_PATH', str(base))

    def build(username, *, reconciliation=None, collect='', extra_files=None):
        user_dir = base / username

        includes = ['include "collect.bean"']
        if reconciliation is not None:
            includes.append('include "reconciliation.bean"')
        for name in (extra_files or {}):
            includes.append(f'include "{name}"')

        _write(user_dir / 'main.bean', MAIN_BEAN)
        _write(user_dir / 'trans/main.bean', '\n'.join(includes) + '\n')

        collect_content = '; header\n\n' + collect if collect else '; header\n'
        _write(user_dir / 'trans/collect.bean', collect_content)

        if reconciliation is not None:
            _write(user_dir / 'trans/reconciliation.bean', reconciliation)

        for name, text in (extra_files or {}).items():
            _write(user_dir / 'trans' / name, text)

        return user_dir

    return build


def test_exact_match_comments_pad(build_ledger):
    """余额与断言完全一致：pad 变为无用，被注释；balance 断言保留。"""
    username = 'cleanupuser'
    user_dir = build_ledger(
        username,
        reconciliation=RECONCILIATION,
        collect=_collect_transaction('205.76'),
    )

    assert _has_unused_pad_error(user_dir / 'main.bean')

    assert ReconciliationCommentService.cleanup_unused_pads(username) == 1

    content = (user_dir / 'trans/reconciliation.bean').read_text(encoding='utf-8')
    assert f'; {PAD_LINE}' in content
    assert BALANCE_LINE in content

    # 清理后不再有无用 pad 错误
    assert not _has_unused_pad_error(user_dir / 'main.bean')

    # 幂等：再次调用不再注释任何行
    assert ReconciliationCommentService.cleanup_unused_pads(username) == 0


def test_within_tolerance_comments_pad(build_ledger):
    """余额与断言相差 0.01（容差内）：同样被识别并注释。"""
    username = 'cleanupuser'
    user_dir = build_ledger(
        username,
        reconciliation=RECONCILIATION,
        collect=_collect_transaction('205.75'),
    )

    assert _has_unused_pad_error(user_dir / 'main.bean')
    assert ReconciliationCommentService.cleanup_unused_pads(username) == 1

    content = (user_dir / 'trans/reconciliation.bean').read_text(encoding='utf-8')
    assert f'; {PAD_LINE}' in content
    assert BALANCE_LINE in content


def test_beyond_tolerance_keeps_pad(build_ledger):
    """余额与断言相差 0.02（超容差）：pad 仍被使用，不注释。"""
    username = 'cleanupuser'
    user_dir = build_ledger(
        username,
        reconciliation=RECONCILIATION,
        collect=_collect_transaction('205.74'),
    )

    # pad 被实际使用，不存在无用 pad 错误
    assert not _has_unused_pad_error(user_dir / 'main.bean')
    assert ReconciliationCommentService.cleanup_unused_pads(username) == 0

    content = (user_dir / 'trans/reconciliation.bean').read_text(encoding='utf-8')
    assert PAD_LINE in content
    assert not content.lstrip().startswith(';')


def test_no_reconciliation_bean_returns_zero(build_ledger):
    """无 reconciliation.bean：直接返回 0。"""
    username = 'cleanupuser'
    build_ledger(
        username,
        reconciliation=None,
        collect=_collect_transaction('205.76'),
    )

    assert ReconciliationCommentService.cleanup_unused_pads(username) == 0


def test_pad_in_other_file_not_touched(build_ledger):
    """无用 pad 位于非 reconciliation.bean 文件：不受影响。"""
    username = 'cleanupuser'
    other_filename = 'other.bean'
    user_dir = build_ledger(
        username,
        reconciliation=None,
        collect=_collect_transaction('205.76'),
        extra_files={other_filename: RECONCILIATION},
    )

    # 其它文件中确实存在被判定为无用的 pad
    assert _has_unused_pad_error(user_dir / 'main.bean')

    # 只处理 reconciliation.bean，故不注释任何行
    assert ReconciliationCommentService.cleanup_unused_pads(username) == 0

    other_content = (user_dir / 'trans' / other_filename).read_text(encoding='utf-8')
    assert PAD_LINE in other_content
