"""
EntryReviewQueueService 用户级统一审核队列服务单元测试
"""
import time

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache

from project.apps.translate.services.copilot_bookkeeping_service import (
    CopilotBookkeepingService,
)
from project.apps.translate.services.entry_review_queue_service import (
    EntryReviewQueueService,
)
from project.apps.translate.services.parse_review_service import ParseReviewService


@pytest.fixture
def queue_user(db):
    """创建队列测试用户"""
    return get_user_model().objects.create_user(
        username='queueuser',
        password='testpass123',
    )


@pytest.fixture
def parse_file_factory(db, queue_user):
    """返回工厂函数：创建 File + ParseFile，返回 file_id"""
    from project.apps.file_manager.models import Directory, File
    from project.apps.translate.models import ParseFile

    state = {'n': 0}

    def _create(name=None):
        state['n'] += 1
        directory, _ = Directory.objects.get_or_create(
            name='queue_dir',
            owner=queue_user,
        )
        fname = name or f'queue_file_{state["n"]}.csv'
        file_obj = File.objects.create(
            name=fname,
            directory=directory,
            storage_name=f'storage_{fname}',
            size=16,
            owner=queue_user,
            content_type='text/csv',
        )
        ParseFile.objects.create(file=file_obj, status='pending_review')
        return file_obj.id

    return _create


def _seed_parse_result(file_id, uuids=('u1',), review_expires_at=None):
    """向解析缓存写入指定 uuid 的条目，制造有效引用"""
    data = {
        'file_id': file_id,
        'formatted_data': [
            {
                'uuid': u,
                'formatted': f'2025-01-20 * "测试" "{u}"\n    Expenses:Test  10.00 CNY\n',
                'original_row': {'date': '2025-01-20', 'amount': 10.00},
            }
            for u in uuids
        ],
        'created_at': time.time(),
    }
    if review_expires_at is not None:
        data['review_expires_at'] = review_expires_at
    assert ParseReviewService.save_parse_result(file_id, data) is True


@pytest.mark.django_db
class TestEntryReviewQueueService:
    """EntryReviewQueueService 单元测试"""

    def setup_method(self):
        """每个用例前清空内存缓存，避免相互污染"""
        cache.clear()

    # ------------------------------------------------------------------
    # 键与引用管理
    # ------------------------------------------------------------------
    def test_queue_key(self):
        assert EntryReviewQueueService._queue_key(7) == 'entry_review_queue:7'

    def test_enqueue_dedup_and_order(self, parse_file_factory):
        """按 (file_id, uuid) 去重追加并保持顺序，返回新增数量"""
        fid1 = parse_file_factory()
        fid2 = parse_file_factory()
        added = EntryReviewQueueService.enqueue(0, [
            {'file_id': fid1, 'uuid': 'u1'},
            {'file_id': fid1, 'uuid': 'u2'},
            {'file_id': fid2, 'uuid': 'u1'},
        ])
        assert added == 3

        # 重复引用不再新增，仅新增新出现的引用
        added2 = EntryReviewQueueService.enqueue(0, [
            {'file_id': fid1, 'uuid': 'u1'},
            {'file_id': fid1, 'uuid': 'u3'},
        ])
        assert added2 == 1

        refs = EntryReviewQueueService._get_refs(0)
        assert [(r['file_id'], r['uuid']) for r in refs] == [
            (fid1, 'u1'),
            (fid1, 'u2'),
            (fid2, 'u1'),
            (fid1, 'u3'),
        ]

    def test_enqueue_skips_incomplete_refs(self):
        """缺少 file_id 或 uuid 的引用被忽略"""
        added = EntryReviewQueueService.enqueue(0, [
            {'file_id': None, 'uuid': 'x'},
            {'file_id': 1, 'uuid': None},
            {'uuid': 'y'},
        ])
        assert added == 0
        assert EntryReviewQueueService._get_refs(0) == []

    def test_list_refs_prunes_stale_refs(self, parse_file_factory):
        """对应 parse_result 缓存失效的引用被剔除并回写"""
        fid1 = parse_file_factory()
        fid2 = parse_file_factory()
        _seed_parse_result(fid1, ['u1'])
        _seed_parse_result(fid2, ['u1'])
        EntryReviewQueueService.enqueue(0, [
            {'file_id': fid1, 'uuid': 'u1'},
            {'file_id': fid2, 'uuid': 'u1'},
        ])

        # 制造 file2 缓存失效
        ParseReviewService.delete_parse_result(fid2)

        refs = EntryReviewQueueService.list_refs(0)
        assert [(r['file_id'], r['uuid']) for r in refs] == [(fid1, 'u1')]
        # 已回写到缓存
        assert EntryReviewQueueService._get_refs(0) == [{'file_id': fid1, 'uuid': 'u1'}]

    def test_remove_file_only_removes_target_file(self, parse_file_factory):
        """remove_file 仅移除指定 file_id 的引用"""
        fid1 = parse_file_factory()
        fid2 = parse_file_factory()
        EntryReviewQueueService.enqueue(0, [
            {'file_id': fid1, 'uuid': 'u1'},
            {'file_id': fid1, 'uuid': 'u2'},
            {'file_id': fid2, 'uuid': 'u1'},
        ])
        EntryReviewQueueService.remove_file(0, fid1)
        refs = EntryReviewQueueService._get_refs(0)
        assert [(r['file_id'], r['uuid']) for r in refs] == [(fid2, 'u1')]

    def test_remove_entries_by_file_and_uuid(self, parse_file_factory):
        """remove_entries 按 (file_id, uuid) 精确移除"""
        fid = parse_file_factory()
        EntryReviewQueueService.enqueue(0, [
            {'file_id': fid, 'uuid': 'u1'},
            {'file_id': fid, 'uuid': 'u2'},
            {'file_id': fid, 'uuid': 'u3'},
        ])
        EntryReviewQueueService.remove_entries(0, [{'file_id': fid, 'uuid': 'u2'}])
        assert [r['uuid'] for r in EntryReviewQueueService._get_refs(0)] == ['u1', 'u3']

    def test_is_empty_and_clear(self, parse_file_factory):
        """is_empty 依据有效引用判断；clear 清空队列"""
        fid = parse_file_factory()
        assert EntryReviewQueueService.is_empty(0) is True

        _seed_parse_result(fid, ['u1'])
        EntryReviewQueueService.enqueue(0, [{'file_id': fid, 'uuid': 'u1'}])
        assert EntryReviewQueueService.is_empty(0) is False

        EntryReviewQueueService.clear(0)
        assert EntryReviewQueueService.is_empty(0) is True

    # ------------------------------------------------------------------
    # 截止时间与条目列表
    # ------------------------------------------------------------------
    def test_earliest_expires_at_returns_min(self, parse_file_factory):
        """多个文件时返回最早的审核截止时间；空队列返回 None"""
        fid1 = parse_file_factory()
        fid2 = parse_file_factory()
        _seed_parse_result(fid1, ['u1'], review_expires_at=2000.0)
        _seed_parse_result(fid2, ['u1'], review_expires_at=1000.0)
        EntryReviewQueueService.enqueue(0, [
            {'file_id': fid1, 'uuid': 'u1'},
            {'file_id': fid2, 'uuid': 'u1'},
        ])
        assert EntryReviewQueueService.earliest_expires_at(0) == 1000.0
        assert EntryReviewQueueService.earliest_expires_at(999) is None

    def test_list_entries_returns_copies_without_polluting_cache(self, parse_file_factory):
        """list_entries 返回带 file_id/file_name 的副本，且不污染缓存原始条目"""
        fid = parse_file_factory(name='明细账.csv')
        _seed_parse_result(fid, ['u1', 'u2'])
        EntryReviewQueueService.enqueue(0, [{'file_id': fid, 'uuid': 'u1'}])

        entries = EntryReviewQueueService.list_entries(0)
        assert len(entries) == 1
        assert entries[0]['uuid'] == 'u1'
        assert entries[0]['file_id'] == fid
        assert entries[0]['file_name'] == '明细账.csv'

        # 缓存中的原始条目不得被写入 file_id / file_name
        cached = ParseReviewService.get_parse_result(fid)
        for entry in cached['formatted_data']:
            assert 'file_id' not in entry
            assert 'file_name' not in entry

    # ------------------------------------------------------------------
    # 用户级锁
    # ------------------------------------------------------------------
    def test_lock_acquire_release(self):
        """首次获取成功，未释放时再次获取失败，释放后可再次获取"""
        uid = 987654
        assert EntryReviewQueueService.acquire_lock(uid, timeout=30, wait=0) is True
        assert EntryReviewQueueService.acquire_lock(uid, timeout=30, wait=0) is False
        EntryReviewQueueService.release_lock(uid)
        assert EntryReviewQueueService.acquire_lock(uid, timeout=30, wait=0) is True

    # ------------------------------------------------------------------
    # 待办辅助
    # ------------------------------------------------------------------
    def test_get_or_create_task_idempotent(self, queue_user):
        """同一用户仅有一条 entry_review 待办"""
        from project.apps.reconciliation.models import ScheduledTask

        task1 = EntryReviewQueueService.get_or_create_task(queue_user)
        task2 = EntryReviewQueueService.get_or_create_task(queue_user)
        assert task1.id == task2.id
        assert task1.status == 'inactive'
        assert ScheduledTask.objects.filter(
            task_type='entry_review',
            object_id=queue_user.id,
        ).count() == 1

    def test_activate_task_sets_pending(self, queue_user):
        """激活待办后状态为 pending"""
        task = EntryReviewQueueService.activate_task(queue_user)
        task.refresh_from_db()
        assert task.status == 'pending'

    def test_complete_task_sets_completed(self, queue_user):
        """完成待办后状态为 completed"""
        EntryReviewQueueService.activate_task(queue_user)
        EntryReviewQueueService.complete_task(queue_user)
        from project.apps.reconciliation.models import ScheduledTask

        task = ScheduledTask.objects.get(
            task_type='entry_review',
            object_id=queue_user.id,
        )
        assert task.status == 'completed'

    def test_deactivate_if_empty_sets_inactive_when_queue_empty(self, queue_user):
        """队列为空时置为 inactive"""
        task = EntryReviewQueueService.activate_task(queue_user)
        assert EntryReviewQueueService.is_empty(queue_user.id) is True
        EntryReviewQueueService.deactivate_if_empty(queue_user)
        task.refresh_from_db()
        assert task.status == 'inactive'

    def test_deactivate_if_empty_keeps_task_pending_when_queue_not_empty(
        self, queue_user, parse_file_factory
    ):
        """队列非空时不应把待办置为 inactive"""
        fid = parse_file_factory()
        _seed_parse_result(fid, ['u1'])
        EntryReviewQueueService.enqueue(queue_user.id, [{'file_id': fid, 'uuid': 'u1'}])
        task = EntryReviewQueueService.activate_task(queue_user)
        assert EntryReviewQueueService.is_empty(queue_user.id) is False

        EntryReviewQueueService.deactivate_if_empty(queue_user)
        task.refresh_from_db()
        assert task.status == 'pending'


def _seed_copilot_staging(user_id, uuids=('c1',), review_expires_at=None):
    """向 Copilot 暂存区写入指定 uuid 的条目，制造有效引用。"""
    data = {
        'formatted_data': [
            {
                'uuid': u,
                'formatted': (
                    f'2025-01-20 * "Copilot" "{u}"\n'
                    '    Expenses:Test  10.00 CNY\n'
                    '    Assets:Test  -10.00 CNY\n'
                ),
                'edited_formatted': (
                    f'2025-01-20 * "Copilot" "{u}"\n'
                    '    Expenses:Test  10.00 CNY\n'
                    '    Assets:Test  -10.00 CNY\n'
                ),
                'original_row': {'date': '2025-01-20', 'amount': 10.00},
            }
            for u in uuids
        ],
        'created_at': time.time(),
    }
    if review_expires_at is not None:
        data['review_expires_at'] = review_expires_at
    assert ParseReviewService.save_parse_result(
        CopilotBookkeepingService.staging_key(user_id), data
    ) is True


@pytest.mark.django_db
class TestEntryReviewQueueServiceSources:
    """统一审核队列两类来源（file / copilot）行为测试"""

    def setup_method(self):
        """每个用例前清空内存缓存，避免相互污染"""
        cache.clear()

    # ------------------------------------------------------------------
    # 来源解析
    # ------------------------------------------------------------------
    def test_ref_source_defaults_to_file(self):
        """历史引用缺少 source 时按账单文件处理"""
        assert EntryReviewQueueService.ref_source({'file_id': 1, 'uuid': 'u1'}) == 'file'
        assert EntryReviewQueueService.ref_source(
            {'source': 'copilot', 'file_id': None, 'uuid': 'x'}
        ) == 'copilot'
        assert EntryReviewQueueService.ref_source({}) == 'file'

    # ------------------------------------------------------------------
    # 入队
    # ------------------------------------------------------------------
    def test_enqueue_mixed_sources_order_and_dedup(self, parse_file_factory):
        """两类来源按入队顺序保存，去重键为 (source, file_id, uuid)"""
        fid = parse_file_factory()
        _seed_parse_result(fid, ['u1'])
        _seed_copilot_staging(0, ['c1'])

        added = EntryReviewQueueService.enqueue(0, [
            {'file_id': fid, 'uuid': 'u1'},
            {'source': 'copilot', 'file_id': None, 'uuid': 'c1'},
        ])
        assert added == 2
        assert EntryReviewQueueService._get_refs(0) == [
            {'file_id': fid, 'uuid': 'u1'},
            {'source': 'copilot', 'file_id': None, 'uuid': 'c1'},
        ]

        # 重复入队（含显式 file 来源）不新增
        assert EntryReviewQueueService.enqueue(0, [
            {'source': 'copilot', 'file_id': None, 'uuid': 'c1'},
            {'source': 'file', 'file_id': fid, 'uuid': 'u1'},
        ]) == 0

    def test_enqueue_skips_file_ref_without_file_id(self):
        """账单来源缺少 file_id 时跳过；copilot 来源允许 file_id 为 None"""
        assert EntryReviewQueueService.enqueue(0, [
            {'file_id': None, 'uuid': 'x'},
            {'source': 'file', 'file_id': None, 'uuid': 'y'},
        ]) == 0
        assert EntryReviewQueueService._get_refs(0) == []

        _seed_copilot_staging(0, ['c1'])
        assert EntryReviewQueueService.enqueue(0, [
            {'source': 'copilot', 'file_id': None, 'uuid': 'c1'},
        ]) == 1

    # ------------------------------------------------------------------
    # 列出引用 / 条目
    # ------------------------------------------------------------------
    def test_list_refs_prunes_stale_file_but_keeps_copilot(self, parse_file_factory):
        """账单缓存失效只剔除该文件引用，copilot 引用保留"""
        fid = parse_file_factory()
        _seed_parse_result(fid, ['u1'])
        _seed_copilot_staging(0, ['c1'])
        EntryReviewQueueService.enqueue(0, [
            {'file_id': fid, 'uuid': 'u1'},
            {'source': 'copilot', 'file_id': None, 'uuid': 'c1'},
        ])

        ParseReviewService.delete_parse_result(fid)

        refs = EntryReviewQueueService.list_refs(0)
        assert refs == [{'source': 'copilot', 'file_id': None, 'uuid': 'c1'}]
        # 已回写剔除后的引用
        assert EntryReviewQueueService._get_refs(0) == refs
        assert CopilotBookkeepingService.has_staging(0) is True

    def test_list_refs_removes_copilot_ref_when_staging_gone(self, parse_file_factory):
        """暂存区失效时剔除 copilot 引用，账单引用不受影响"""
        fid = parse_file_factory()
        _seed_parse_result(fid, ['u1'])
        _seed_copilot_staging(0, ['c1'])
        EntryReviewQueueService.enqueue(0, [
            {'file_id': fid, 'uuid': 'u1'},
            {'source': 'copilot', 'file_id': None, 'uuid': 'c1'},
        ])

        CopilotBookkeepingService.clear(0)

        assert EntryReviewQueueService.list_refs(0) == [{'file_id': fid, 'uuid': 'u1'}]

    def test_list_entries_mixed_sources(self, parse_file_factory):
        """list_entries 按队列顺序返回两类条目并补充来源字段"""
        fid = parse_file_factory(name='混合账.csv')
        _seed_parse_result(fid, ['u1'])
        _seed_copilot_staging(0, ['c1', 'c2'])
        EntryReviewQueueService.enqueue(0, [
            {'file_id': fid, 'uuid': 'u1'},
            {'source': 'copilot', 'file_id': None, 'uuid': 'c2'},
        ])

        entries = EntryReviewQueueService.list_entries(0)
        assert [e['uuid'] for e in entries] == ['u1', 'c2']

        file_entry = entries[0]
        assert file_entry['source'] == 'file'
        assert file_entry['file_id'] == fid
        assert file_entry['file_name'] == '混合账.csv'

        copilot_entry = entries[1]
        assert copilot_entry['source'] == 'copilot'
        assert copilot_entry['file_id'] is None
        assert copilot_entry['file_name'] == CopilotBookkeepingService.SOURCE_LABEL

    # ------------------------------------------------------------------
    # 最早截止时间
    # ------------------------------------------------------------------
    def test_earliest_expires_at_considers_both_sources(self, parse_file_factory):
        """最早截止时间同时覆盖两类来源"""
        fid = parse_file_factory()
        _seed_parse_result(fid, ['u1'], review_expires_at=5000.0)
        _seed_copilot_staging(0, ['c1'], review_expires_at=2000.0)
        EntryReviewQueueService.enqueue(0, [
            {'file_id': fid, 'uuid': 'u1'},
            {'source': 'copilot', 'file_id': None, 'uuid': 'c1'},
        ])
        assert EntryReviewQueueService.earliest_expires_at(0) == 2000.0

        # 账单更早时返回账单截止时间
        _seed_parse_result(fid, ['u1'], review_expires_at=1000.0)
        assert EntryReviewQueueService.earliest_expires_at(0) == 1000.0

    def test_earliest_expires_at_none_when_no_refs(self):
        assert EntryReviewQueueService.earliest_expires_at(4242) is None

    # ------------------------------------------------------------------
    # 移除引用
    # ------------------------------------------------------------------
    def test_remove_file_keeps_copilot_refs(self, parse_file_factory):
        """remove_file 只移除账单来源引用"""
        fid1 = parse_file_factory()
        fid2 = parse_file_factory()
        _seed_parse_result(fid1, ['u1'])
        _seed_parse_result(fid2, ['u1'])
        _seed_copilot_staging(0, ['c1'])
        EntryReviewQueueService.enqueue(0, [
            {'file_id': fid1, 'uuid': 'u1'},
            {'source': 'copilot', 'file_id': None, 'uuid': 'c1'},
            {'file_id': fid2, 'uuid': 'u1'},
        ])

        EntryReviewQueueService.remove_file(0, fid1)

        assert EntryReviewQueueService._get_refs(0) == [
            {'source': 'copilot', 'file_id': None, 'uuid': 'c1'},
            {'file_id': fid2, 'uuid': 'u1'},
        ]

    def test_remove_entries_matches_source(self, parse_file_factory):
        """remove_entries 按 (source, file_id, uuid) 精确移除；无 source 按 file 处理"""
        fid = parse_file_factory()
        _seed_parse_result(fid, ['u1'])
        _seed_copilot_staging(0, ['c1', 'c2'])
        EntryReviewQueueService.enqueue(0, [
            {'file_id': fid, 'uuid': 'u1'},
            {'source': 'copilot', 'file_id': None, 'uuid': 'c1'},
            {'source': 'copilot', 'file_id': None, 'uuid': 'c2'},
        ])

        # 无 source 的 ref 被视作 file 来源，不会误删 copilot 引用
        EntryReviewQueueService.remove_entries(0, [{'file_id': None, 'uuid': 'c1'}])
        assert [r.get('uuid') for r in EntryReviewQueueService._get_refs(0)] == [
            'u1', 'c1', 'c2'
        ]

        EntryReviewQueueService.remove_entries(0, [
            {'source': 'copilot', 'file_id': None, 'uuid': 'c1'},
        ])
        assert EntryReviewQueueService._get_refs(0) == [
            {'file_id': fid, 'uuid': 'u1'},
            {'source': 'copilot', 'file_id': None, 'uuid': 'c2'},
        ]

    def test_remove_entries_by_file_and_uuid(self, parse_file_factory):
        """账单来源 remove_entries 仍按 (file_id, uuid) 精确移除"""
        fid = parse_file_factory()
        _seed_parse_result(fid, ['u1', 'u2'])
        EntryReviewQueueService.enqueue(0, [
            {'file_id': fid, 'uuid': 'u1'},
            {'file_id': fid, 'uuid': 'u2'},
        ])
        EntryReviewQueueService.remove_entries(0, [{'source': 'file', 'file_id': fid, 'uuid': 'u2'}])
        assert EntryReviewQueueService._get_refs(0) == [{'file_id': fid, 'uuid': 'u1'}]

    # ------------------------------------------------------------------
    # 历史引用与空判断
    # ------------------------------------------------------------------
    def test_legacy_refs_without_source_treated_as_file(self, parse_file_factory):
        """历史缓存中缺 source 的引用按 file 处理，且与显式 file 引用同键"""
        fid = parse_file_factory(name='历史账.csv')
        _seed_parse_result(fid, ['u1'])
        EntryReviewQueueService._save_refs(0, [{'file_id': fid, 'uuid': 'u1'}])

        refs = EntryReviewQueueService.list_refs(0)
        assert refs == [{'file_id': fid, 'uuid': 'u1'}]
        assert EntryReviewQueueService.ref_source(refs[0]) == 'file'

        entries = EntryReviewQueueService.list_entries(0)
        assert entries[0]['source'] == 'file'
        assert entries[0]['file_id'] == fid
        assert entries[0]['file_name'] == '历史账.csv'

        assert EntryReviewQueueService.enqueue(0, [
            {'source': 'file', 'file_id': fid, 'uuid': 'u1'},
        ]) == 0

    def test_is_empty_and_clear_with_copilot_only(self):
        _seed_copilot_staging(0, ['c1'])
        EntryReviewQueueService.enqueue(0, [
            {'source': 'copilot', 'file_id': None, 'uuid': 'c1'},
        ])
        assert EntryReviewQueueService.is_empty(0) is False

        EntryReviewQueueService.clear(0)
        assert EntryReviewQueueService.is_empty(0) is True
