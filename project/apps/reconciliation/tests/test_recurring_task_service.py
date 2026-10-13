"""
RecurringTaskService 循环待办服务测试
"""
import pytest
from datetime import date, timedelta

from django.contrib.contenttypes.models import ContentType

from project.apps.account.models import Account
from project.apps.reconciliation.models import RecurringTask, ScheduledTask
from project.apps.reconciliation.services.recurrence import RecurrenceParseError
from project.apps.reconciliation.services.recurring_task_service import RecurringTaskService


# ---- create ----

@pytest.mark.django_db
def test_create_normalizes_rule(user):
    """有效规则：rrule 归一化、状态 active"""
    start = date(2026, 1, 1)
    defn = RecurringTaskService.create(user, 'every 3 days', start_date=start)

    assert defn.user == user
    assert defn.rule_text == 'every 3 days'
    assert defn.rrule == 'FREQ=DAILY;INTERVAL=3'
    assert defn.start_date == start
    assert defn.status == 'active'


@pytest.mark.django_db
def test_create_invalid_rule_raises_and_creates_nothing(user):
    """无效规则：抛出 RecurrenceParseError 且不落库"""
    with pytest.raises(RecurrenceParseError):
        RecurringTaskService.create(user, 'foo bar')

    assert RecurringTask.objects.count() == 0


@pytest.mark.django_db
def test_create_explicit_basis_override(user):
    """显式 basis 覆盖解析结果"""
    defn = RecurringTaskService.create(user, 'every 3 days', basis='completed')
    assert defn.recurrence_basis == 'completed'


# ---- update / delete ----

@pytest.mark.django_db
def test_update_reparses_rule(user):
    defn = RecurringTaskService.create(user, 'every 3 days', start_date=date(2026, 1, 1))

    RecurringTaskService.update(
        defn, rule_text='every week on Tuesday'
    )
    defn.refresh_from_db()

    assert defn.rule_text == 'every week on Tuesday'
    assert defn.rrule.startswith('FREQ=WEEKLY')


@pytest.mark.django_db
def test_update_start_date(user):
    defn = RecurringTaskService.create(user, 'every 3 days', start_date=date(2026, 1, 1))

    RecurringTaskService.update(defn, start_date=date(2026, 2, 1))
    defn.refresh_from_db()

    assert defn.start_date == date(2026, 2, 1)


@pytest.mark.django_db
def test_delete_cancels_pending(user):
    today = date.today()
    defn = RecurringTaskService.create(
        user, 'every 3 days', start_date=today - timedelta(days=1)
    )
    RecurringTaskService.generate_due(today=today)
    defn_id = defn.id

    RecurringTaskService.delete(defn, cancel_pending=True)

    assert not RecurringTask.objects.filter(id=defn_id).exists()
    assert not ScheduledTask.objects.filter(
        task_type='recurring', object_id=defn_id, status='pending'
    ).exists()


# ---- generate_due ----

def _make_active_definition(user, rule_text, rrule, start_date):
    """直接落库定义（绕过 create 的即时对齐），用于测试定时扫描"""
    return RecurringTask.objects.create(
        user=user,
        rule_text=rule_text,
        rrule=rrule,
        recurrence_basis='scheduled',
        start_date=start_date,
        status='active',
    )


@pytest.mark.django_db
def test_generate_due_creates_one_instance(user):
    today = date.today()
    defn = _make_active_definition(
        user, 'every 3 days', 'FREQ=DAILY;INTERVAL=3', today - timedelta(days=1)
    )

    created = RecurringTaskService.generate_due(today=today)
    defn.refresh_from_db()

    assert created == 1
    assert defn.generated_count == 1
    # 下一次生成日期由「最近一次待办日期 + rrule」动态推算
    assert RecurringTaskService.next_generation_date(defn) > today
    assert ScheduledTask.objects.filter(
        task_type='recurring', object_id=defn.id, status='pending'
    ).count() == 1


@pytest.mark.django_db
def test_generate_due_skips_when_pending_exists(user):
    today = date.today()
    defn = _make_active_definition(
        user, 'every 3 days', 'FREQ=DAILY;INTERVAL=3', today - timedelta(days=1)
    )

    assert RecurringTaskService.generate_due(today=today) == 1
    # 仍有待执行实例：不重复生成
    assert RecurringTaskService.generate_due(today=today) == 0
    assert ScheduledTask.objects.filter(
        task_type='recurring', object_id=defn.id, status='pending'
    ).count() == 1


@pytest.mark.django_db
def test_generate_due_creates_at_most_one_pending(user):
    """同时只保留一个待执行实例：再次运行不再生成（逐期推进，不堆积）"""
    today = date.today()
    defn = _make_active_definition(
        user, 'every 3 days', 'FREQ=DAILY;INTERVAL=3', today - timedelta(days=30)
    )

    assert RecurringTaskService.generate_due(today=today) == 1
    assert RecurringTaskService.generate_due(today=today) == 0
    assert ScheduledTask.objects.filter(
        task_type='recurring', object_id=defn.id, status='pending'
    ).count() == 1


@pytest.mark.django_db
def test_generate_due_marks_ended_when_rule_exhausted(user):
    """规则不可满足（2 月 30 日）：不生成实例并把定义置为已结束"""
    today = date.today()
    defn = _make_active_definition(
        user,
        'every February on the 30th',
        'FREQ=YEARLY;BYMONTH=2;BYMONTHDAY=30',
        today - timedelta(days=1),
    )

    created = RecurringTaskService.generate_due(today=today)
    defn.refresh_from_db()

    assert created == 0
    assert defn.status == 'ended'
    assert RecurringTaskService.next_generation_date(defn) is None


# ---- complete_instance ----

@pytest.mark.django_db
def test_complete_instance_scheduled_basis_returns_next_date(user):
    """按计划基准：完成后返回「上一次待办日期 + rrule」"""
    defn = RecurringTaskService.create(user, 'every 3 days', start_date=date(2026, 1, 1))

    RecurringTaskService.generate_due(today=date(2026, 1, 2))
    task = ScheduledTask.objects.get(task_type='recurring', object_id=defn.id)

    result = RecurringTaskService.complete_instance(task, completed_date=date(2026, 1, 2))

    assert result == {'completed': task.id, 'next_date': '2026-01-04'}


@pytest.mark.django_db
def test_complete_instance_completed_basis_advances_from_completion(user):
    """按完成基准（when done）：以完成日期为锚点重新起算下一次发生"""
    start = date(2026, 1, 1)
    defn = RecurringTaskService.create(user, 'every 10 days when done', start_date=start)
    assert defn.recurrence_basis == 'completed'

    RecurringTaskService.generate_due(today=date(2026, 1, 5))
    task = ScheduledTask.objects.get(task_type='recurring', object_id=defn.id)

    result = RecurringTaskService.complete_instance(task, completed_date=date(2026, 1, 20))
    defn.refresh_from_db()

    assert result == {'completed': task.id, 'next_date': '2026-01-30'}
    assert defn.status == 'active'


@pytest.mark.django_db
def test_complete_instance_generates_next_when_due(user):
    """完成后下一期已到期：立即生成下一期待办（every day）"""
    today = date.today()
    yesterday = today - timedelta(days=1)
    defn = RecurringTaskService.create(user, 'every day', start_date=yesterday)

    task = ScheduledTask.objects.get(
        task_type='recurring', object_id=defn.id, status='pending'
    )
    assert task.scheduled_date == yesterday

    result = RecurringTaskService.complete_instance(task, completed_date=today)

    # 下一期（今天）已到期：立即生成新的 pending，无需等定时扫描
    assert result == {'completed': task.id, 'next_date': today.isoformat()}
    task.refresh_from_db()
    assert task.status == 'completed'
    next_task = ScheduledTask.objects.get(
        task_type='recurring', object_id=defn.id, status='pending'
    )
    assert next_task.scheduled_date == today


@pytest.mark.django_db
def test_complete_instance_does_not_generate_before_due(user):
    """完成后下一期未到期：不提前生成待办"""
    today = date.today()
    defn = RecurringTaskService.create(user, 'every month', start_date=today)

    task = ScheduledTask.objects.get(
        task_type='recurring', object_id=defn.id, status='pending'
    )

    result = RecurringTaskService.complete_instance(task, completed_date=today)

    assert result['next_date'] is not None
    assert not ScheduledTask.objects.filter(
        task_type='recurring', object_id=defn.id, status='pending'
    ).exists()


# ---- next_run_date（管理页展示的下一次执行日期） ----

@pytest.mark.django_db
def test_next_run_date_not_generated_is_start_date(user):
    """未生成：管理页日期就是「本期待办日期」= start_date（has_pending=False）"""
    from project.apps.reconciliation.serializers import RecurringTaskSerializer

    defn = RecurringTaskService.create(
        user, 'every month on the 1st', start_date=date(2027, 3, 20)
    )

    data = RecurringTaskSerializer(defn).data
    assert data['has_pending'] is False
    assert data['next_run_date'] == '2027-03-20'


@pytest.mark.django_db
def test_off_rule_start_due_generates_at_start_date(user):
    """every month on the 25th：基准日期到期 → 生成日期=基准日期本身（不再取整到 25 日）"""
    from project.apps.reconciliation.serializers import RecurringTaskSerializer

    today = date(2026, 10, 13)
    defn = _make_active_definition(
        user, 'every month on the 25th', 'FREQ=MONTHLY;BYMONTHDAY=25', today
    )
    RecurringTaskService._align_schedule(defn, today=today)
    defn.refresh_from_db()

    task = ScheduledTask.objects.get(
        task_type='recurring', object_id=defn.id, status='pending'
    )
    assert task.scheduled_date == today
    # 下一次 = 本期待办日期 + rrule（本月 25 日）
    assert RecurringTaskSerializer(defn).data['next_run_date'] == '2026-10-25'


@pytest.mark.django_db
def test_off_rule_start_future_keeps_start_date(user):
    """every month on the 25th：基准日期未到期 → 不生成，管理页显示基准日期本身"""
    from project.apps.reconciliation.serializers import RecurringTaskSerializer

    defn = _make_active_definition(
        user, 'every month on the 25th', 'FREQ=MONTHLY;BYMONTHDAY=25', date(2026, 10, 26)
    )

    data = RecurringTaskSerializer(defn).data
    assert data['has_pending'] is False
    assert data['next_run_date'] == '2026-10-26'


@pytest.mark.django_db
def test_next_run_date_pending_scheduled_uses_fixed_grid(user):
    """已生成且为计划基准：展示待办日期之后的下一次（每月 1 日 → 下月 1 日）"""
    from project.apps.reconciliation.serializers import RecurringTaskSerializer

    defn = RecurringTaskService.create(
        user, 'every month on the 1st', start_date=date(2026, 1, 1)
    )
    ScheduledTask.objects.create(
        task_type='recurring',
        content_type=ContentType.objects.get_for_model(RecurringTask),
        object_id=defn.id,
        scheduled_date=date(2026, 10, 1),
        status='pending',
    )

    data = RecurringTaskSerializer(defn).data
    assert data['has_pending'] is True
    assert data['next_run_date'] == '2026-11-01'


@pytest.mark.django_db
def test_next_run_date_pending_completed_anchors_today(user):
    """已生成且为 when done：以今天为锚点重新起算（今天 + 1 个月）"""
    from dateutil.relativedelta import relativedelta
    from project.apps.reconciliation.serializers import RecurringTaskSerializer

    today = date.today()
    defn = RecurringTaskService.create(
        user, 'every month when done', start_date=date(2026, 1, 1)
    )
    ScheduledTask.objects.create(
        task_type='recurring',
        content_type=ContentType.objects.get_for_model(RecurringTask),
        object_id=defn.id,
        scheduled_date=today,
        status='pending',
    )

    data = RecurringTaskSerializer(defn).data
    assert data['has_pending'] is True
    assert data['next_run_date'] == (today + relativedelta(months=1)).isoformat()


@pytest.mark.django_db
def test_create_with_default_date_generates_instance(user):
    """默认日期（today）新建：立即生成待办，展示完成后下一次日期（需求 1）"""
    from dateutil.relativedelta import relativedelta
    from project.apps.reconciliation.serializers import RecurringTaskSerializer

    today = date.today()
    defn = RecurringTaskService.create(user, 'every month')

    data = RecurringTaskSerializer(defn).data
    assert data['has_pending'] is True
    task = ScheduledTask.objects.get(
        task_type='recurring', object_id=defn.id, status='pending'
    )
    assert task.scheduled_date == today
    assert data['next_run_date'] == (today + relativedelta(months=1)).isoformat()


@pytest.mark.django_db
def test_update_start_to_past_scheduled_generates_and_advances(user):
    """every month：start 改到过去 → 立即生成，展示下一次待办开始日期（需求 2.1/3.2）"""
    from dateutil.relativedelta import relativedelta
    from project.apps.reconciliation.serializers import RecurringTaskSerializer

    today = date.today()
    first_of_month = date(today.year, today.month, 1)
    defn = RecurringTaskService.create(
        user, 'every month', start_date=today + timedelta(days=3)
    )
    assert RecurringTaskService.has_pending(defn) is False

    RecurringTaskService.update(defn, start_date=first_of_month)
    defn.refresh_from_db()

    assert RecurringTaskService.has_pending(defn) is True
    task = ScheduledTask.objects.get(
        task_type='recurring', object_id=defn.id, status='pending'
    )
    assert task.scheduled_date == first_of_month
    assert RecurringTaskSerializer(defn).data['next_run_date'] == (
        first_of_month + relativedelta(months=1)
    ).isoformat()


@pytest.mark.django_db
def test_update_start_to_past_when_done_anchors_today(user):
    """every month when done：start 改到过去 → 立即生成，展示今天 + rrule（需求 2.2/3.1）"""
    from dateutil.relativedelta import relativedelta
    from project.apps.reconciliation.serializers import RecurringTaskSerializer

    today = date.today()
    first_of_month = date(today.year, today.month, 1)
    defn = RecurringTaskService.create(
        user, 'every month when done', start_date=today + timedelta(days=3)
    )
    assert RecurringTaskService.has_pending(defn) is False

    RecurringTaskService.update(defn, start_date=first_of_month)
    defn.refresh_from_db()

    assert RecurringTaskService.has_pending(defn) is True
    assert RecurringTaskSerializer(defn).data['next_run_date'] == (
        today + relativedelta(months=1)
    ).isoformat()


@pytest.mark.django_db
def test_update_start_to_future_cancels_pending_and_shows_start(user):
    """start 改到未来：取消待办，日期回到可修改的下一次生成日期（=start）（需求 2.3）"""
    from project.apps.reconciliation.serializers import RecurringTaskSerializer

    today = date.today()
    tomorrow = today + timedelta(days=1)
    defn = RecurringTaskService.create(user, 'every month', start_date=today)
    assert RecurringTaskService.has_pending(defn) is True

    RecurringTaskService.update(defn, start_date=tomorrow)
    defn.refresh_from_db()

    assert RecurringTaskService.has_pending(defn) is False
    assert not ScheduledTask.objects.filter(
        task_type='recurring', object_id=defn.id, status='pending'
    ).exists()
    data = RecurringTaskSerializer(defn).data
    assert data['has_pending'] is False
    assert data['next_run_date'] == tomorrow.isoformat()


@pytest.mark.django_db
def test_complete_then_move_start_earlier(user):
    """完成昨日实例后，仍可把定义日期调早并立即生成新待办（历史实例不得锚死日期）"""
    today = date.today()
    yesterday = today - timedelta(days=1)
    defn = RecurringTaskService.create(user, 'every 3 days', start_date=yesterday)

    task = ScheduledTask.objects.get(
        task_type='recurring', object_id=defn.id, status='pending'
    )
    assert task.scheduled_date == yesterday

    RecurringTaskService.complete_instance(task, completed_date=today)
    defn.refresh_from_db()
    # 完成后仅按「本次预期日期 + DSL」推进，不参考已完成实例
    assert defn.start_date == today + timedelta(days=2)
    assert RecurringTaskService.has_pending(defn) is False

    # 调到过去：应直接生效并立即生成新的待办
    earlier = today - timedelta(days=10)
    RecurringTaskService.update(defn, start_date=earlier)
    defn.refresh_from_db()

    assert defn.start_date == earlier
    assert RecurringTaskService.has_pending(defn) is True
    pending = ScheduledTask.objects.get(
        task_type='recurring', object_id=defn.id, status='pending'
    )
    assert pending.scheduled_date == earlier


@pytest.mark.django_db
def test_next_generation_date_ignores_completed_instances(user):
    """next_generation_date 不参考已完成实例：只由定义预期日期 + DSL 决定"""
    today = date.today()
    defn = RecurringTaskService.create(
        user, 'every 3 days', start_date=today + timedelta(days=5)
    )
    assert RecurringTaskService.next_generation_date(defn) == today + timedelta(days=5)

    ScheduledTask.objects.create(
        task_type='recurring',
        content_type=ContentType.objects.get_for_model(RecurringTask),
        object_id=defn.id,
        scheduled_date=today - timedelta(days=100),
        completed_date=today - timedelta(days=100),
        status='completed',
    )

    assert RecurringTaskService.next_generation_date(defn) == today + timedelta(days=5)


@pytest.mark.django_db
def test_complete_instance_non_recurring_raises(user, account):
    """非循环待办调用完成接口应报错"""
    ct = ContentType.objects.get_for_model(Account)
    task = ScheduledTask.objects.create(
        task_type='reconciliation',
        content_type=ct,
        object_id=account.id,
        scheduled_date=date.today(),
        status='pending',
    )

    with pytest.raises(ValueError, match='该待办不是循环待办'):
        RecurringTaskService.complete_instance(task)


# ---- 状态过滤 ----

@pytest.mark.django_db
def test_ended_definition_is_skipped(user):
    """非 active 的定义不生成实例"""
    today = date.today()
    defn = RecurringTaskService.create(
        user, 'every 3 days', start_date=today - timedelta(days=1)
    )

    defn.status = 'ended'
    defn.save()

    assert RecurringTaskService.generate_due(today=today) == 0


# ---- preview ----

@pytest.mark.django_db
def test_preview_returns_increasing_dates(user):
    defn = RecurringTaskService.create(user, 'every 3 days', start_date=date(2026, 1, 1))

    dates = RecurringTaskService.preview(defn, count=3, after=date(2026, 1, 1))

    assert dates == [date(2026, 1, 4), date(2026, 1, 7), date(2026, 1, 10)]
    assert dates == sorted(dates)


def test_preview_text_shape():
    result = RecurringTaskService.preview_text(
        'every 3 days', start_date=date(2026, 1, 1), count=2, after=date(2026, 1, 1)
    )

    assert result['rule_text'] == 'every 3 days'
    assert result['describe'] == '每 3 天'
    assert result['basis'] == 'scheduled'
    assert result['next_occurrences'] == ['2026-01-04', '2026-01-07']


def test_preview_text_notify_consequence():
    """notify：到期只立即生成一条；未到期不生成；规则不可满足则 ended"""
    today = date(2026, 10, 13)

    due = RecurringTaskService.preview_text(
        'every month', start_date=today, kind='notify', today=today
    )
    assert due['first_occurrence'] == '2026-10-13'
    assert due['immediate_dates'] == ['2026-10-13']
    assert due['next_expected_date'] is None
    assert due['ended'] is False

    future = RecurringTaskService.preview_text(
        'every month', start_date=date(2026, 10, 15), kind='notify', today=today
    )
    assert future['immediate_dates'] == []
    assert future['first_occurrence'] == '2026-10-15'

    endless = RecurringTaskService.preview_text(
        'every February on the 30th', start_date=today, kind='notify', today=today
    )
    assert endless['ended'] is True
    assert endless['first_occurrence'] is None


def test_preview_text_generate_review_backfills_all_due():
    """generate_review：补齐所有已到期周期，并把预期日期推进到未来"""
    today = date(2026, 10, 13)

    result = RecurringTaskService.preview_text(
        'every month', start_date=date(2026, 9, 1), kind='generate_review', today=today
    )

    assert result['immediate_dates'] == ['2026-09-01', '2026-10-01']
    assert result['next_expected_date'] == '2026-11-01'

