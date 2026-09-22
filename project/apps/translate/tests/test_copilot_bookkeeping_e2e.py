"""Copilot 记账端到端集成测试（真实链路，不 mock 服务/队列/审核 API）。

覆盖 checklist「端到端」检查点：
对话记账 → 生成 entry_review 待办 → 审核页确认 → trans/collect.bean
追加写入、待办完成，全链路可复现。

链路全部使用真实实现：
- AssistantService._dispatch_tool('record_transaction', ...)
- CopilotBookkeepingService（暂存区）
- EntryReviewQueueService（统一审核队列 + entry_review 待办）
- EntryReview 审核 API（results / confirm）

仅把 settings.ASSETS_BASE_PATH 指向临时目录，避免污染真实 Assets/。
"""
from pathlib import Path

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from rest_framework import status
from rest_framework.test import APIClient

from project.apps.account.models import Account
from project.apps.assistant.services.assistant_service import AssistantService
from project.apps.reconciliation.models import ScheduledTask
from project.apps.translate.services.copilot_bookkeeping_service import (
    CopilotBookkeepingService,
)
from project.apps.translate.services.entry_review_queue_service import (
    EntryReviewQueueService,
)
from project.utils.file import BeanFileManager

User = get_user_model()

EXPENSE_ACCOUNT = 'Expenses:Food:Lunch'
ASSET_ACCOUNT = 'Assets:WeChat'
COLLECT_HEADER = '; Trans directory - Auto-generated includes'


@pytest.fixture
def temp_assets(tmp_path, monkeypatch):
    """把 ASSETS_BASE_PATH 指向临时目录，隔离 collect.bean 写入。"""
    base = tmp_path / 'Assets'
    base.mkdir()
    monkeypatch.setattr(settings, 'ASSETS_BASE_PATH', str(base))
    return base


@pytest.mark.django_db
def test_copilot_bookkeeping_full_chain(user, temp_assets):
    """对话记账 → 待办 pending → 审核确认 → collect.bean 追加 → 待办 completed。"""
    # ----------------------------------------------------------------
    # 1. 准备：账户目录 + 账本结构（含 trans/collect.bean）
    # ----------------------------------------------------------------
    Account.objects.create(account=EXPENSE_ACCOUNT, owner=user, enable=True)
    Account.objects.create(account=ASSET_ACCOUNT, owner=user, enable=True)

    BeanFileManager.init_user_bean_structure(user)

    collect_path = Path(BeanFileManager.get_collect_bean_path(user))
    trans_main_path = Path(BeanFileManager.get_trans_main_bean_path(user))
    assert collect_path.exists()
    assert COLLECT_HEADER in collect_path.read_text(encoding='utf-8')
    assert 'include "collect.bean"' in trans_main_path.read_text(encoding='utf-8')
    # 记录确认前的文件内容，用于验证是追加而非覆盖
    collect_before = collect_path.read_text(encoding='utf-8')

    # ----------------------------------------------------------------
    # 2. 对话记账：走真实的 AssistantService 工具分发
    # ----------------------------------------------------------------
    assistant = AssistantService(user)
    text = assistant._dispatch_tool(
        'record_transaction',
        {
            'entries': [
                {
                    'type': 'expense',
                    'date': '2026-01-02',
                    'amount': 25,
                    'narration': '午餐',
                    'payee': '食堂',
                    'account': EXPENSE_ACCOUNT,
                    'payment_account': ASSET_ACCOUNT,
                }
            ]
        },
        [],
    )

    assert '待审核条目共 1 条' in text
    assert 'collect.bean' in text

    # ----------------------------------------------------------------
    # 3. 中间态：entry_review 待办 pending + 队列中 copilot 引用与条目
    # ----------------------------------------------------------------
    content_type = ContentType.objects.get_for_model(User)
    task = ScheduledTask.objects.get(
        task_type='entry_review', content_type=content_type, object_id=user.id
    )
    assert task.status == 'pending'

    refs = EntryReviewQueueService.list_refs(user.id)
    assert len(refs) == 1
    assert refs[0]['source'] == 'copilot'
    assert refs[0]['file_id'] is None

    entries = EntryReviewQueueService.list_entries(user.id)
    assert len(entries) == 1
    staged_entry = entries[0]
    assert staged_entry['source'] == 'copilot'
    assert staged_entry['file_id'] is None
    assert staged_entry['file_name'] == 'Copilot 记账'
    entry_text = staged_entry['formatted'].rstrip()
    assert EXPENSE_ACCOUNT in entry_text
    assert ASSET_ACCOUNT in entry_text

    # 确认写入前，collect.bean 未被改动
    assert collect_path.read_text(encoding='utf-8') == collect_before

    # ----------------------------------------------------------------
    # 4. 审核页：results 返回 copilot 条目 → confirm 确认写入
    # ----------------------------------------------------------------
    client = APIClient()
    client.force_authenticate(user=user)

    results_response = client.get('/api/translate/entry-review/results')
    assert results_response.status_code == status.HTTP_200_OK
    assert results_response.data['entry_count'] == 1
    reviewed_entry = results_response.data['entries'][0]
    assert reviewed_entry['source'] == 'copilot'
    assert reviewed_entry['file_id'] is None
    assert reviewed_entry['file_name'] == 'Copilot 记账'

    confirm_response = client.post('/api/translate/entry-review/confirm')
    assert confirm_response.status_code == status.HTTP_200_OK

    # ----------------------------------------------------------------
    # 5. 终态：collect.bean 追加写入 + 暂存区清理 + 队列清空 + 待办完成
    # ----------------------------------------------------------------
    collect_after = collect_path.read_text(encoding='utf-8')

    # 追加而非覆盖：原注释头与确认前内容仍在
    assert COLLECT_HEADER in collect_after
    assert collect_after.startswith(collect_before)
    # 新条目文本已写入
    assert entry_text in collect_after
    assert EXPENSE_ACCOUNT in collect_after
    assert ASSET_ACCOUNT in collect_after

    # trans/main.bean 仍包含 include "collect.bean"
    assert 'include "collect.bean"' in trans_main_path.read_text(encoding='utf-8')

    # Copilot 暂存区被删除、队列清空、待办完成
    assert CopilotBookkeepingService.has_staging(user.id) is False
    assert EntryReviewQueueService.list_refs(user.id) == []
    task.refresh_from_db()
    assert task.status == 'completed'
