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
    """有效规则：rrule 归一化，next_date==start_date，状态 active"""
    start = date(2026, 1, 1)
    defn = RecurringTaskService.create(user, '喝水', 'every 3 days', start_date=start)

    assert defn.user == user
    assert defn.rule_text == 'every 3 days'
    assert defn.rrule == 'FREQ=DAILY;INTERVAL=3'
    assert defn.start_date == start
    assert defn.next_date == start
    assert defn.status == 'active'


@pytest.mark.django_db
def test_create_invalid_rule_raises_and_creates_nothing(user):
    """无效规则：抛出 RecurrenceParseError 且不落库"""
    with pytest.raises(RecurrenceParseError):
        RecurringTaskService.create(user, '喝水', 'foo bar')

    assert RecurringTask.objects.count() == 0


@pytest.mark.django_db
def test_create_explicit_basis_override(user):
    """显式 basis 覆盖解析结果"""
    defn = RecurringTaskService.create(user, '喝水', 'every 3 days', basis='completed')
    assert defn.recurrence_basis == 'completed'


# ---- update / delete ----

@pytest.mark.django_db
def test_update_reparses_rule(user):
    defn = RecurringTaskService.create(user, '旧标题', 'every 3 days', start_date=date(2026, 1, 1))

    RecurringTaskService.update(
        defn, title='新标题', rule_text='every week on Tuesday'
    )
    defn.refresh_from_db()

    assert defn.title == '新标题'
    assert defn.rule_text == 'every week on Tuesday'
    assert defn.rrule.startswith('FREQ=WEEKLY')


@pytest.mark.django_db
def test_update_start_date_resets_next_date(user):
    defn = RecurringTaskService.create(user, '喝水', 'every 3 days', start_date=date(2026, 1, 1))

    RecurringTaskService.update(defn, start_date=date(2026, 2, 1))
    defn.refresh_from_db()

    assert defn.start_date == date(2026, 2, 1)
    assert defn.next_date == date(2026, 2, 1)


@pytest.mark.django_db
def test_delete_cancels_pending(user):
    today = date.today()
    defn = RecurringTaskService.create(
        user, '喝水', 'every 3 days', start_date=today - timedelta(days=1)
    )
    RecurringTaskService.generate_due(today=today)
    defn_id = defn.id

    RecurringTaskService.delete(defn, cancel_pending=True)

    assert not RecurringTask.objects.filter(id=defn_id).exists()
    assert not ScheduledTask.objects.filter(
        task_type='recurring', object_id=defn_id, status='pending'
    ).exists()


# ---- generate_due ----

@pytest.mark.django_db
def test_generate_due_creates_one_instance(user):
    today = date.today()
    defn = RecurringTaskService.create(
        user, '喝水', 'every 3 days', start_date=today - timedelta(days=1)
    )

    created = RecurringTaskService.generate_due(today=today)
    defn.refresh_from_db()

    assert created == 1
    assert defn.generated_count == 1
    assert defn.next_date > today
    assert ScheduledTask.objects.filter(
        task_type='recurring', object_id=defn.id, status='pending'
    ).count() == 1


@pytest.mark.django_db
def test_generate_due_skips_when_pending_exists(user):
    today = date.today()
    defn = RecurringTaskService.create(
        user, '喝水', 'every 3 days', start_date=today - timedelta(days=1)
    )

    assert RecurringTaskService.generate_due(today=today) == 1
    # 仍有待执行实例：不重复生成
    assert RecurringTaskService.generate_due(today=today) == 0
    assert ScheduledTask.objects.filter(
        task_type='recurring', object_id=defn.id, status='pending'
    ).count() == 1


@pytest.mark.django_db
def test_generate_due_overdue_multiple_periods(user):
    today = date.today()
    defn = RecurringTaskService.create(
        user, '喝水', 'every 3 days', start_date=today - timedelta(days=30)
    )

    created = RecurringTaskService.generate_due(today=today)
    defn.refresh_from_db()

    # 逾期多期仍只生成 1 个实例，并把 next_date 推进到今天之后
    assert created == 1
    assert defn.next_date > today
    assert ScheduledTask.objects.filter(
        task_type='recurring', object_id=defn.id, status='pending'
    ).count() == 1


@pytest.mark.django_db
def test_generate_due_marks_ended_when_rule_exhausted(user):
    """规则不可满足（2 月 30 日）时推进为 None，定义结束"""
    today = date.today()
    defn = RecurringTaskService.create(
        user, '不存在', 'every February on the 30th', start_date=today - timedelta(days=1)
    )

    created = RecurringTaskService.generate_due(today=today)
    defn.refresh_from_db()

    assert created == 1
    assert defn.status == 'ended'
    assert defn.next_date is None


# ---- complete_instance ----

@pytest.mark.django_db
def test_complete_instance_scheduled_basis_keeps_next_date(user):
    """按计划基准：完成实例后 next_date 保持在生成时已推进的值"""
    start = date(2026, 1, 1)
    defn = RecurringTaskService.create(user, '交房租', 'every 3 days', start_date=start)

    RecurringTaskService.generate_due(today=date(2026, 1, 2))
    task = ScheduledTask.objects.get(task_type='recurring', object_id=defn.id)
    defn.refresh_from_db()
    advanced = defn.next_date

    result = RecurringTaskService.complete_instance(task, completed_date=date(2026, 1, 2))
    defn.refresh_from_db()

    assert result == {'completed': task.id, 'next_date': advanced}
    assert defn.next_date == advanced


@pytest.mark.django_db
def test_complete_instance_completed_basis_advances_from_completion(user):
    """按完成基准：next_date 重算为完成日期之后的下一次发生"""
    start = date(2026, 1, 1)
    defn = RecurringTaskService.create(user, '健身', 'every 10 days when done', start_date=start)
    assert defn.recurrence_basis == 'completed'

    RecurringTaskService.generate_due(today=date(2026, 1, 5))
    task = ScheduledTask.objects.get(task_type='recurring', object_id=defn.id)

    result = RecurringTaskService.complete_instance(task, completed_date=date(2026, 1, 20))
    defn.refresh_from_db()

    assert result == {'completed': task.id, 'next_date': date(2026, 1, 21)}
    assert defn.next_date == date(2026, 1, 21)
    assert defn.status == 'active'


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


# ---- pause / resume ----

@pytest.mark.django_db
def test_paused_definition_is_skipped(user):
    today = date.today()
    defn = RecurringTaskService.create(
        user, '喝水', 'every 3 days', start_date=today - timedelta(days=1)
    )

    RecurringTaskService.pause(defn)
    assert defn.status == 'paused'

    assert RecurringTaskService.generate_due(today=today) == 0


@pytest.mark.django_db
def test_resume_sets_active_and_restores_next_date(user):
    defn = RecurringTaskService.create(user, '喝水', 'every 3 days', start_date=date(2026, 1, 1))
    RecurringTaskService.pause(defn)
    defn.next_date = None
    defn.save()

    RecurringTaskService.resume(defn)

    assert defn.status == 'active'
    assert defn.next_date == defn.start_date


# ---- preview ----

@pytest.mark.django_db
def test_preview_returns_increasing_dates(user):
    defn = RecurringTaskService.create(user, '喝水', 'every 3 days', start_date=date(2026, 1, 1))

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
