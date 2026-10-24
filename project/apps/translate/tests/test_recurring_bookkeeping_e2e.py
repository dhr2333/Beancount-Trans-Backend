"""循环待办「生成审核待办」端到端测试（真实链路，不 mock）。

覆盖：RecurringTask(kind='generate_review') 到期 → 固定模板原样入统一审核队列
→ entry_review 待办 pending → 审核页确认 → trans/collect.bean 追加写入、待办完成；
以及「永不过期、不自动写入」。

仅把 settings.ASSETS_BASE_PATH 指向临时目录，避免污染真实 Assets/。
"""
from datetime import date, timedelta
from pathlib import Path

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from rest_framework import status
from rest_framework.test import APIClient

from project.apps.reconciliation.models import ScheduledTask
from project.apps.reconciliation.services import RecurringTaskService
from project.apps.translate.services.entry_review_queue_service import (
    EntryReviewQueueService,
)
from project.apps.translate.services.recurring_bookkeeping_service import (
    RecurringBookkeepingService,
)
from project.utils.file import BeanFileManager

User = get_user_model()

COLLECT_HEADER = '; Trans directory - Auto-generated includes'
TEMPLATE = (
    '2026-01-01 * "测试" "固定模板"\n'
    '    Expenses:Food:Lunch                          10.00 CNY\n'
    '    Assets:WeChat                               -10.00 CNY'
)


@pytest.fixture
def temp_assets(tmp_path, monkeypatch):
    """把 ASSETS_BASE_PATH 指向临时目录，隔离 collect.bean 写入。"""
    base = tmp_path / 'Assets'
    base.mkdir()
    monkeypatch.setattr(settings, 'ASSETS_BASE_PATH', str(base))
    return base


def _make_review_kind_definition(user):
    """创建一个到期的 generate_review 定义（模板固定文本）。"""
    return RecurringTaskService.create(
        user,
        'every month',
        note='模板标题',
        start_date=date.today() - timedelta(days=1),
        kind='generate_review',
        template=TEMPLATE,
    )


@pytest.mark.django_db
def test_recurring_generate_review_full_chain(user, temp_assets):
    """到期生成审核条目 → 审核确认 → collect.bean 追加 → 待办完成。"""
    BeanFileManager.init_user_bean_structure(user)
    collect_path = Path(BeanFileManager.get_collect_bean_path(user))
    assert COLLECT_HEADER in collect_path.read_text(encoding='utf-8')
    collect_before = collect_path.read_text(encoding='utf-8')

    defn = _make_review_kind_definition(user)

    # 生成即推进：不留 pending 循环卡片，锚点已完成后计入 generated_count
    assert RecurringTaskService.has_pending(defn) is False
    assert defn.generated_count == 1

    content_type = ContentType.objects.get_for_model(User)
    task = ScheduledTask.objects.get(
        task_type='entry_review', content_type=content_type, object_id=user.id
    )
    assert task.status == 'pending'

    refs = EntryReviewQueueService.list_refs(user.id)
    assert len(refs) == 1
    assert refs[0]['source'] == 'recurring'
    assert refs[0]['file_id'] is None

    entries = EntryReviewQueueService.list_entries(user.id)
    assert len(entries) == 1
    assert entries[0]['source'] == 'recurring'
    assert entries[0]['file_name'] == '模板标题'
    # 模板原样：无占位符替换、无语法校验
    assert entries[0]['formatted'] == TEMPLATE

    # 永不过期：无审核截止时间，不参与自动写入
    assert EntryReviewQueueService.earliest_expires_at(user.id) is None

    # 确认前 collect.bean 未被改动
    assert collect_path.read_text(encoding='utf-8') == collect_before

    client = APIClient()
    client.force_authenticate(user=user)

    results = client.get('/api/translate/entry-review/results')
    assert results.status_code == status.HTTP_200_OK
    assert results.data['entry_count'] == 1
    assert results.data['entries'][0]['source'] == 'recurring'
    assert results.data['review_expires_at'] is None

    # 编辑循环条目：写回循环暂存区，不应报「文件不存在」
    entry_uuid = results.data['entries'][0]['uuid']
    edited_text = TEMPLATE.replace('固定模板', '编辑后的模板')
    edit = client.put(
        f'/api/translate/entry-review/entries/{entry_uuid}/edit',
        {'source': 'recurring', 'file_id': None, 'edited_formatted': edited_text},
        format='json',
    )
    assert edit.status_code == status.HTTP_200_OK
    assert edit.data['source'] == 'recurring'
    assert edit.data['file_id'] is None
    assert RecurringBookkeepingService.get_entry(user.id, entry_uuid)['edited_formatted'] == edited_text

    confirm = client.post('/api/translate/entry-review/confirm')
    assert confirm.status_code == status.HTTP_200_OK

    collect_after = collect_path.read_text(encoding='utf-8')
    assert collect_after.startswith(collect_before)
    assert edited_text in collect_after

    assert RecurringBookkeepingService.has_staging(user.id) is False
    assert EntryReviewQueueService.list_refs(user.id) == []
    task.refresh_from_db()
    assert task.status == 'completed'


@pytest.mark.django_db
def test_auto_confirm_skips_recurring(user, temp_assets):
    """到期自动写入任务跳过 recurring 来源：引用保留、待办仍 pending、不写账本。"""
    BeanFileManager.init_user_bean_structure(user)
    collect_path = Path(BeanFileManager.get_collect_bean_path(user))

    _make_review_kind_definition(user)

    from project.apps.translate.tasks import auto_confirm_expired_entry_reviews

    auto_confirm_expired_entry_reviews()

    assert len(EntryReviewQueueService.list_refs(user.id)) == 1
    assert len(EntryReviewQueueService.list_entries(user.id)) == 1

    content_type = ContentType.objects.get_for_model(User)
    task = ScheduledTask.objects.get(
        task_type='entry_review', content_type=content_type, object_id=user.id
    )
    assert task.status == 'pending'

    assert TEMPLATE not in collect_path.read_text(encoding='utf-8')
