"""
EntryReviewQueueService 用户级统一审核队列服务单元测试
"""
import time

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache

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
