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
    def create(user, rule_text, note='', start_date=None, basis=None,
               kind='notify', template='') -> RecurringTask:
        """创建循环待办定义；规则无法解析时抛出 RecurrenceParseError"""
        spec = RecurrenceParser.parse(rule_text)
        if basis is not None:
            spec.basis = basis
        start_date = start_date or date.today()
        defn = RecurringTask.objects.create(
            user=user,
            note=note,
            kind=kind or 'notify',
            template=template or '',
            rule_text=rule_text,
            rrule=spec.to_rrule_string(),
            recurrence_basis=spec.basis,
            start_date=start_date,
            status='active',
        )
        # 立即对齐：默认 start_date=today 时通常会立刻生成待执行实例
        RecurringTaskService._align_schedule(defn)
        return defn

    @staticmethod
    def update(defn, **fields) -> RecurringTask:
        """更新循环待办定义（允许 note/kind/template/rule_text/start_date/recurrence_basis）"""
        if 'note' in fields:
            defn.note = fields['note']
        if fields.get('kind'):
            defn.kind = fields['kind']
        if 'template' in fields:
            defn.template = fields['template'] or ''

        if fields.get('rule_text'):
            spec = RecurrenceParser.parse(fields['rule_text'])
            defn.rule_text = fields['rule_text']
            defn.rrule = spec.to_rrule_string()
            # 未显式指定基准时，采用规则解析出的基准
            if 'recurrence_basis' not in fields:
                defn.recurrence_basis = spec.basis

        if fields.get('recurrence_basis'):
            defn.recurrence_basis = fields['recurrence_basis']

        start_date_changed = bool(fields.get('start_date'))
        if start_date_changed:
            defn.start_date = fields['start_date']

        defn.save()
        # 修改 start_date 后立即对齐：取消旧实例，必要时按新日期重新生成
        if start_date_changed:
            RecurringTaskService._align_schedule(defn)
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

    # ---- 展示标签 ----

    @staticmethod
    def label(defn) -> str:
        """定义的展示标签（卡片/审核条目文本单一来源）

        依次取 note / template 的首个非空行（截断 128 字符）；
        都为空时回退规则中文描述，解析失败返回「循环待办」。
        """
        for text in (defn.note, defn.template):
            stripped = (text or '').strip()
            if stripped:
                return stripped.splitlines()[0][:128]
        try:
            return RecurrenceParser.parse(defn.rule_text).describe()
        except Exception:
            return '循环待办'

    # ---- 预览 ----

    @staticmethod
    def preview(defn, count=5, after=None) -> list:
        """预览定义的后续 count 次发生日期"""
        spec = RecurrenceParser.parse(defn.rule_text)
        after = after or date.today()
        return RecurrenceCalculator.next_occurrences(spec, defn.start_date, after, count)

    @staticmethod
    def preview_text(rule_text, start_date=None, count=5, after=None,
                     kind='notify', today=None) -> dict:
        """预览未持久化规则的描述、后续发生日期，以及「创建后的即时后果」

        后果（immediate_dates / next_expected_date）由 _simulate_alignment 无副作用地
        模拟 _align_schedule 得出，供前端在提交前把不可逆副作用前置展示。
        """
        start_date = start_date or date.today()
        after = after or date.today()
        today = today or after
        spec = RecurrenceParser.parse(rule_text)
        occurrences = RecurrenceCalculator.next_occurrences(spec, start_date, after, count)
        satisfiable = RecurrenceCalculator.first_on_or_after(spec, start_date) is not None
        immediate, next_expected = RecurringTaskService._simulate_alignment(
            spec, start_date, kind, today
        )
        return {
            'rule_text': rule_text,
            'describe': spec.describe(),
            'basis': spec.basis,
            'next_occurrences': [d.isoformat() for d in occurrences],
            'first_occurrence': start_date.isoformat() if satisfiable else None,
            'immediate_dates': [d.isoformat() for d in immediate],
            'next_expected_date': next_expected.isoformat() if next_expected else None,
            'ended': not satisfiable,
        }

    @staticmethod
    def _simulate_alignment(spec, start_date, kind, today) -> tuple[list, date | None]:
        """无副作用地模拟 _align_schedule，返回 (会立即生成的日期, 推进后的预期日期)

        本期待办日期即 start_date：到期（start_date <= today）时生成该日期的实例。
        - notify：只生成一个待执行实例后等待用户完成，不推进预期日期
        - generate_review：补齐所有已到期周期，直到预期日期落在未来
        """
        if RecurrenceCalculator.first_on_or_after(spec, start_date) is None:
            return [], None
        immediate: list[date] = []
        cursor_start = start_date
        cand = start_date
        while cand is not None and cand <= today:
            immediate.append(cand)
            if kind != 'generate_review':
                return immediate, None
            nxt = RecurrenceCalculator.next_occurrence(spec, cursor_start, cand)
            if nxt is None:
                return immediate, None
            cursor_start = nxt
            cand = nxt
        return immediate, (cand if kind == 'generate_review' else None)

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
        """下一次生成待办的日期（动态推算，不入库）

        各实例之间不相互关联，只依据「定义的本期待办日期 start_date」与
        「当前待执行实例的预期日期」推算，不参考任何已完成/已取消的历史实例，
        以免历史实例把日期锚死（导致无法把日期往更早调整）：
        - 无待执行实例：就是「本期待办日期」= start_date（不再向上取整到规则日，
          否则 `every month on the 25th` 设 2026-10-13 会被取整成 2026-10-25 而不生成）；
          规则不可满足（无任何发生日）时返回 None
        - scheduled 基准：待执行实例日期之后的下一次发生
        - completed（when done）基准：以待执行实例日期重新起算的下一次发生
        """
        spec = RecurrenceParser.parse(defn.rule_text)
        pending = RecurringTaskService._instances(defn).filter(status='pending').first()
        if pending is None:
            # 规则不可满足（如 every February on the 30th）→ 定义应结束
            if RecurrenceCalculator.first_on_or_after(spec, defn.start_date) is None:
                return None
            return defn.start_date
        if defn.recurrence_basis == 'scheduled':
            return RecurrenceCalculator.next_occurrence(
                spec, defn.start_date, pending.scheduled_date
            )
        anchor = pending.completed_date or pending.scheduled_date
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

    # ---- 即时对齐 ----

    @staticmethod
    def _generate_instance(defn, due_date):
        """按到期产出类型生成本期实例，返回本期实例

        - kind='notify'：创建 pending 循环卡片（现状行为），待用户完成后推进
        - kind='generate_review'：把固定模板并入统一审核队列，并创建一个已完成
          实例作为历史记录；由于没有 pending 可等待完成，生成即把定义的下一次
          预期日期推进到下一周期
        """
        ct = ContentType.objects.get_for_model(RecurringTask)
        if defn.kind == 'generate_review':
            from project.apps.translate.services.recurring_bookkeeping_service import (
                RecurringBookkeepingService,
            )

            RecurringBookkeepingService.generate_for_definition(defn.user, defn, due_date)
            task = ScheduledTask.objects.create(
                task_type='recurring',
                content_type=ct,
                object_id=defn.id,
                scheduled_date=due_date,
                completed_date=due_date,
                status='completed',
            )
            # 生成即推进：下一周期只依据「定义的下一次预期日期 + DSL」前移
            spec = RecurrenceParser.parse(defn.rule_text)
            nxt = RecurrenceCalculator.next_occurrence(spec, defn.start_date, due_date)
            if nxt is not None:
                defn.start_date = nxt
        else:
            task = ScheduledTask.objects.create(
                task_type='recurring',
                content_type=ct,
                object_id=defn.id,
                scheduled_date=due_date,
                status='pending',
            )
        defn.last_generated_task = task
        defn.generated_count += 1
        defn.save(update_fields=['last_generated_task', 'generated_count', 'start_date'])
        return task

    @staticmethod
    def _align_schedule(defn, today=None) -> None:
        """按当前 start_date / rrule 立即对齐待办实例

        创建定义或修改 start_date 后调用：
        1. 取消该定义下所有待执行实例（置 cancelled，保留历史不删除）
        2. 仅依据新的 start_date 推算下一次生成日期（不参考任何历史实例）
        3. 若该日期 <= 今天则生成实例；notify 只生成一个待执行实例即停止，
           generate_review 则补齐所有已到期周期，最终让下一次预期日期落在未来
        """
        today = today or date.today()
        ct = ContentType.objects.get_for_model(RecurringTask)

        ScheduledTask.objects.filter(
            task_type='recurring',
            content_type=ct,
            object_id=defn.id,
            status='pending',
        ).update(status='cancelled')

        cand = RecurringTaskService.next_generation_date(defn)
        while cand is not None and cand <= today:
            RecurringTaskService._generate_instance(defn, cand)
            # notify 生成一个待执行实例后即等待用户完成，不继续推进；
            # generate_review 无待执行实例可等待，需补齐所有已到期周期，
            # 使定义的下一次预期日期永远落在未来（否则会残留过期日期）
            if defn.kind != 'generate_review':
                break
            cand = RecurringTaskService.next_generation_date(defn)

        if cand is None:
            # 规则耗尽：结束定义
            if defn.status == 'active':
                defn.status = 'ended'
                defn.save(update_fields=['status'])

    @staticmethod
    def reschedule(defn, new_start_date, today=None) -> RecurringTask:
        """顺延定义：把 start_date 改为 new_start_date 并立即对齐

        用于用户在「循环」待办卡片上修改执行日期：等价于把该循环顺延到新日期，
        旧实例被取消；若新日期已到期则立即生成新实例。
        """
        defn.start_date = new_start_date
        defn.save(update_fields=['start_date'])
        RecurringTaskService._align_schedule(defn, today=today)
        return defn

    # ---- 实例生成 / 完成 ----

    @staticmethod
    def generate_due(today=None) -> int:
        """扫描活跃定义并生成到期实例，返回本次生成的实例数"""
        today = today or date.today()
        created = 0

        for defn in RecurringTask.objects.filter(status='active'):
            # 已存在待执行实例：等待用户完成，不再生成（同时只允许一个未完成实例）
            if RecurringTaskService.has_pending(defn):
                continue

            cand = RecurringTaskService.next_generation_date(defn)
            if cand is None:
                # 规则耗尽（如每月 30 日遇到 2 月），结束定义
                defn.status = 'ended'
                defn.save()
                continue

            if cand > today:
                continue

            RecurringTaskService._generate_instance(defn, cand)
            created += 1

        return created

    @staticmethod
    def complete_instance(task, completed_date=None) -> dict:
        """完成循环待办实例：把定义的下一次预期日期推进到下一周期

        各实例之间不相互关联，只依据「本次实例的预期日期 / 完成日期 + DSL」推进：
        - scheduled 基准：以定义预期日期为 dtstart，取本次实例预期日期之后的下一次
        - completed（when done）基准：以本次完成日期为锚点重新起算下一次
        完成后若下一期已到期（<= 完成日期），立即生成下一期待办，使其立刻出现在
        待办列表，而不必等待定时扫描。
        """
        if task.task_type != 'recurring':
            raise ValueError('该待办不是循环待办')

        completed_date = completed_date or date.today()
        task.status = 'completed'
        task.completed_date = completed_date
        task.save()

        defn = task.content_object
        if not isinstance(defn, RecurringTask):
            return {'completed': task.id, 'next_date': None}

        spec = RecurrenceParser.parse(defn.rule_text)
        if defn.recurrence_basis == 'scheduled':
            nxt = RecurrenceCalculator.next_occurrence(
                spec, defn.start_date, task.scheduled_date
            )
        else:
            nxt = RecurrenceCalculator.next_occurrence(
                spec, completed_date, completed_date
            )

        if nxt is None:
            if defn.status == 'active':
                defn.status = 'ended'
                defn.save(update_fields=['status'])
            return {'completed': task.id, 'next_date': None}

        defn.start_date = nxt
        defn.save(update_fields=['start_date'])
        if nxt <= completed_date:
            # 到期即生成：完成本期后立即推进下一期
            RecurringTaskService._generate_instance(defn, nxt)
        return {
            'completed': task.id,
            'next_date': nxt.isoformat(),
        }
