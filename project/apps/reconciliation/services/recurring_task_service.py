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
    def create(user, title, rule_text, note='', start_date=None, basis=None,
               kind='notify', template_ref='') -> RecurringTask:
        """创建循环待办定义；规则无法解析时抛出 RecurrenceParseError"""
        spec = RecurrenceParser.parse(rule_text)
        if basis is not None:
            spec.basis = basis
        start_date = start_date or date.today()
        return RecurringTask.objects.create(
            user=user,
            title=title,
            note=note,
            kind=kind,
            template_ref=template_ref or '',
            rule_text=rule_text,
            rrule=spec.to_rrule_string(),
            recurrence_basis=spec.basis,
            start_date=start_date,
            next_date=start_date,
            status='active',
        )

    @staticmethod
    def update(defn, **fields) -> RecurringTask:
        """更新循环待办定义（允许 title/note/kind/template_ref/rule_text/start_date/recurrence_basis）"""
        if 'title' in fields:
            defn.title = fields['title']
        if 'note' in fields:
            defn.note = fields['note']
        if 'kind' in fields:
            defn.kind = fields['kind']
        if 'template_ref' in fields:
            defn.template_ref = fields['template_ref'] or ''

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
            defn.next_date = fields['start_date']

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

    # ---- 实例生成 / 完成 ----

    @staticmethod
    def generate_due(today=None) -> int:
        """扫描到期的活动定义并生成实例，返回本次生成的实例数"""
        today = today or date.today()
        ct = ContentType.objects.get_for_model(RecurringTask)
        created = 0

        definitions = RecurringTask.objects.filter(
            status='active',
            next_date__isnull=False,
            next_date__lte=today,
        )
        for defn in definitions:
            # 已存在待执行实例：不重复生成，也不推进（等待用户完成）
            pending_exists = ScheduledTask.objects.filter(
                task_type='recurring',
                content_type=ct,
                object_id=defn.id,
                status='pending',
            ).exists()
            if pending_exists:
                continue

            task = ScheduledTask.objects.create(
                task_type='recurring',
                content_type=ct,
                object_id=defn.id,
                scheduled_date=defn.next_date,
                status='pending',
            )
            defn.last_generated_task = task
            defn.generated_count += 1

            # 仅按计划基准在生成时推进；按完成基准留给 complete_instance 计算
            if defn.recurrence_basis == 'scheduled':
                RecurringTaskService._advance_definition(defn, today)

            defn.save()
            created += 1

        return created

    @staticmethod
    def _advance_definition(defn, today) -> None:
        """按计划基准把 next_date 推进到 today 之后；规则耗尽则结束定义"""
        spec = RecurrenceParser.parse(defn.rule_text)
        base = defn.next_date
        while base is not None and base <= today:
            base = RecurrenceCalculator.next_occurrence(spec, defn.start_date, base)
        if base is None:
            defn.status = 'ended'
            defn.next_date = None
        else:
            defn.next_date = base

    @staticmethod
    def complete_instance(task, completed_date=None) -> dict:
        """完成循环待办实例，并按基准推进其定义的下次生成日期"""
        if task.task_type != 'recurring':
            raise ValueError('该待办不是循环待办')

        completed_date = completed_date or date.today()
        task.status = 'completed'
        task.completed_date = completed_date
        task.save()

        defn = task.content_object
        if isinstance(defn, RecurringTask) and defn.status == 'active':
            if defn.recurrence_basis == 'completed':
                # 按完成基准：以实际完成日期为锚点重算下次生成日期
                spec = RecurrenceParser.parse(defn.rule_text)
                nxt = RecurrenceCalculator.next_occurrence(
                    spec, defn.start_date, completed_date
                )
                if nxt is None:
                    defn.status = 'ended'
                    defn.next_date = None
                else:
                    defn.next_date = nxt
                defn.save()
            # 按计划基准：next_date 已在生成时推进，保持不变

        return {
            'completed': task.id,
            'next_date': defn.next_date if isinstance(defn, RecurringTask) else None,
        }
