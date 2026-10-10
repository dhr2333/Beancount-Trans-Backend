"""
循环待办服务

管理 RecurringTask 定义的增删改查、暂停/恢复、预览，以及到期的实例生成
（generate_due）与实例完成（complete_instance）。
规则解析与日期计算复用 recurrence.py 中的 RecurrenceParser / RecurrenceCalculator。
"""
from datetime import date

from django.contrib.contenttypes.models import ContentType

from project.apps.reconciliation.models import RecurringTask, ScheduledTask
from .recurrence import RecurrenceParser, RecurrenceCalculator


class RecurringTaskService:
    """循环待办服务：定义管理与实例生成/完成"""

    # ---- 定义管理 ----

    @staticmethod
    def create(user, title, rule_text, note='', start_date=None, basis=None) -> RecurringTask:
        """创建循环待办定义；规则无法解析时抛出 RecurrenceParseError"""
        spec = RecurrenceParser.parse(rule_text)
        if basis is not None:
            spec.basis = basis
        start_date = start_date or date.today()
        return RecurringTask.objects.create(
            user=user,
            title=title,
            note=note,
            rule_text=rule_text,
            rrule=spec.to_rrule_string(),
            recurrence_basis=spec.basis,
            start_date=start_date,
            status='active',
        )

    @staticmethod
    def update(defn, **fields) -> RecurringTask:
        """更新循环待办定义（允许 title/note/rule_text/start_date/recurrence_basis）"""
        if 'title' in fields:
            defn.title = fields['title']
        if 'note' in fields:
            defn.note = fields['note']

        if fields.get('rule_text'):
            spec = RecurrenceParser.parse(fields['rule_text'])
            defn.rule_text = fields['rule_text']
            defn.rrule = spec.to_rrule_string()
            # 未显式指定基准时，采用规则解析出的基准
            if 'recurrence_basis' not in fields:
                defn.recurrence_basis = spec.basis

        if fields.get('recurrence_basis'):
            defn.recurrence_basis = fields['recurrence_basis']

        if fields.get('start_date'):
            defn.start_date = fields['start_date']

        defn.save()
        return defn

    @staticmethod
    def delete(defn, cancel_pending=True) -> None:
        """删除定义；默认取消其所有待执行的实例"""
        if cancel_pending:
            ct = ContentType.objects.get_for_model(RecurringTask)
            ScheduledTask.objects.filter(
                task_type='recurring',
                content_type=ct,
                object_id=defn.id,
                status='pending',
            ).update(status='cancelled')
        defn.delete()

    # ---- 预览 ----

    @staticmethod
    def preview(defn, count=5, after=None) -> list:
        """预览定义的后续 count 次发生日期"""
        spec = RecurrenceParser.parse(defn.rule_text)
        after = after or date.today()
        return RecurrenceCalculator.next_occurrences(spec, defn.start_date, after, count)

    @staticmethod
    def preview_text(rule_text, start_date=None, count=5, after=None) -> dict:
        """预览未持久化规则的描述与后续发生日期（供前端即时预览）"""
        start_date = start_date or date.today()
        after = after or date.today()
        spec = RecurrenceParser.parse(rule_text)
        occurrences = RecurrenceCalculator.next_occurrences(spec, start_date, after, count)
        return {
            'rule_text': rule_text,
            'describe': spec.describe(),
            'basis': spec.basis,
            'next_occurrences': [d.isoformat() for d in occurrences],
        }

    # ---- 日期推算 ----

    @staticmethod
    def _instances(defn):
        """该定义下的全部循环实例（按 scheduled_date 倒序）"""
        ct = ContentType.objects.get_for_model(RecurringTask)
        return ScheduledTask.objects.filter(
            task_type='recurring',
            content_type=ct,
            object_id=defn.id,
        ).order_by('-scheduled_date', '-id')

    @staticmethod
    def latest_instance(defn):
        """最近一次已生成的实例（按 scheduled_date 取最新），无则 None"""
        return RecurringTaskService._instances(defn).first()

    @staticmethod
    def has_pending(defn) -> bool:
        """是否存在待执行实例"""
        ct = ContentType.objects.get_for_model(RecurringTask)
        return ScheduledTask.objects.filter(
            task_type='recurring',
            content_type=ct,
            object_id=defn.id,
            status='pending',
        ).exists()

    @staticmethod
    def next_generation_date(defn, today=None) -> date | None:
        """下一次生成待办的日期（由「最近一次待办日期」结合 rrule 动态推算，不入库）

        - 从未生成：以 start_date 为种子取首个发生日
        - scheduled 基准：上一次待办日期之后的下一次发生
        - completed（when done）基准：上一次完成日期之后的下一次发生
        """
        spec = RecurrenceParser.parse(defn.rule_text)
        latest = RecurringTaskService.latest_instance(defn)
        if latest is None:
            return RecurrenceCalculator.first_on_or_after(spec, defn.start_date)
        if defn.recurrence_basis == 'scheduled':
            return RecurrenceCalculator.next_occurrence(
                spec, defn.start_date, latest.scheduled_date
            )
        anchor = latest.completed_date or latest.scheduled_date
        return RecurrenceCalculator.next_occurrence(spec, anchor, anchor)

    @staticmethod
    def display_next_date(defn, today=None) -> date | None:
        """管理页展示用的「下一次执行日期」

        - 已生成（存在待执行实例）：展示完成后推算的下一次
          - scheduled：待办日期之后的下一次
          - completed：假定今天完成 → 以今天为锚点
        - 还没到：展示下一次生成日期
        """
        today = today or date.today()
        pending = RecurringTaskService._instances(defn).filter(status='pending').first()
        if pending is None:
            return RecurringTaskService.next_generation_date(defn)
        spec = RecurrenceParser.parse(defn.rule_text)
        if defn.recurrence_basis == 'scheduled':
            return RecurrenceCalculator.next_occurrence(
                spec, defn.start_date, pending.scheduled_date
            )
        return RecurrenceCalculator.next_occurrence(spec, today, today)

    # ---- 实例生成 / 完成 ----

    @staticmethod
    def generate_due_for(defn, today=None) -> bool:
        """对单个定义做一次到期检查：无待执行实例且候选日期已到 → 生成实例

        返回是否生成了实例。定义非 active / 已有待执行实例 / 候选日期未到均不生成。
        """
        today = today or date.today()
        if defn.status != 'active':
            return False
        # 已存在待执行实例：等待用户完成，不再生成（同时只允许一个未完成实例）
        if RecurringTaskService.has_pending(defn):
            return False

        cand = RecurringTaskService.next_generation_date(defn)
        if cand is None:
            # 规则耗尽（如每月 30 日遇到 2 月），结束定义
            defn.status = 'ended'
            defn.save()
            return False
        if cand > today:
            return False

        task = ScheduledTask.objects.create(
            task_type='recurring',
            content_type=ContentType.objects.get_for_model(RecurringTask),
            object_id=defn.id,
            scheduled_date=cand,
            status='pending',
        )
        defn.last_generated_task = task
        defn.generated_count += 1
        defn.save()
        return True

    @staticmethod
    def generate_due(today=None) -> int:
        """扫描活跃定义并生成到期实例，返回本次生成的实例数"""
        today = today or date.today()
        created = 0
        for defn in RecurringTask.objects.filter(status='active'):
            if RecurringTaskService.generate_due_for(defn, today=today):
                created += 1
        return created

    @staticmethod
    def complete_instance(task, completed_date=None) -> dict:
        """完成循环待办实例；返回下一次生成日期（动态推算，不落库）"""
        if task.task_type != 'recurring':
            raise ValueError('该待办不是循环待办')

        completed_date = completed_date or date.today()
        task.status = 'completed'
        task.completed_date = completed_date
        task.save()

        defn = task.content_object
        if not isinstance(defn, RecurringTask):
            return {'completed': task.id, 'next_date': None}

        nxt = RecurringTaskService.next_generation_date(defn)
        if nxt is None and defn.status == 'active':
            defn.status = 'ended'
            defn.save()
        return {
            'completed': task.id,
            'next_date': nxt.isoformat() if nxt else None,
        }
