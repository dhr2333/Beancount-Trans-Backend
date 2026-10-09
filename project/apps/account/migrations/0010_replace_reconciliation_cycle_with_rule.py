"""
用 DSL 规则字段 reconciliation_rule 取代对账周期字段
（reconciliation_cycle_unit / reconciliation_cycle_interval）。

- 新增 reconciliation_rule（Account 与 AccountTemplateItem）
- 数据迁移：把存量 (unit, interval) 转为等价 DSL：``every {interval} {unit}``
- 移除旧的 unit/interval 字段
"""
import re

from django.db import migrations, models


# 旧「单位 + 间隔」→ DSL 规则
def _cycle_to_rule(unit, interval):
    if not unit or not interval:
        return ''
    return f'every {interval} {unit}'


# 简易 DSL → (unit, interval)（仅能还原 ``every N days|weeks|months|years``）
_SIMPLE_RULE_RE = re.compile(r'^every\s+(\d+)\s+(days|weeks|months|years)$')


def forwards(apps, schema_editor):
    """存量对账周期 → reconciliation_rule"""
    Account = apps.get_model('account_config', 'Account')
    AccountTemplateItem = apps.get_model('account_config', 'AccountTemplateItem')

    for Model in (Account, AccountTemplateItem):
        for obj in Model.objects.all():
            rule = _cycle_to_rule(
                obj.reconciliation_cycle_unit,
                obj.reconciliation_cycle_interval,
            )
            if rule:
                obj.reconciliation_rule = rule
                obj.save(update_fields=['reconciliation_rule'])


def backwards(apps, schema_editor):
    """reconciliation_rule → 存量对账周期（尽力还原）"""
    Account = apps.get_model('account_config', 'Account')
    AccountTemplateItem = apps.get_model('account_config', 'AccountTemplateItem')

    for Model in (Account, AccountTemplateItem):
        for obj in Model.objects.all():
            match = _SIMPLE_RULE_RE.match((obj.reconciliation_rule or '').strip().lower())
            if match:
                obj.reconciliation_cycle_interval = int(match.group(1))
                obj.reconciliation_cycle_unit = match.group(2)
                obj.save(update_fields=[
                    'reconciliation_cycle_interval',
                    'reconciliation_cycle_unit',
                ])


class Migration(migrations.Migration):

    dependencies = [
        ('account_config', '0009_account_description_accounttemplateitem_description'),
    ]

    operations = [
        migrations.AddField(
            model_name='account',
            name='reconciliation_rule',
            field=models.CharField(
                blank=True,
                default='',
                help_text='受控自然语言循环规则，如 every month on the last',
                max_length=128,
                verbose_name='对账周期规则',
            ),
        ),
        migrations.AddField(
            model_name='accounttemplateitem',
            name='reconciliation_rule',
            field=models.CharField(
                blank=True,
                default='',
                help_text='受控自然语言循环规则，如 every month on the last',
                max_length=128,
                verbose_name='对账周期规则',
            ),
        ),
        migrations.RunPython(forwards, backwards),
        migrations.RemoveField(
            model_name='account',
            name='reconciliation_cycle_unit',
        ),
        migrations.RemoveField(
            model_name='account',
            name='reconciliation_cycle_interval',
        ),
        migrations.RemoveField(
            model_name='accounttemplateitem',
            name='reconciliation_cycle_unit',
        ),
        migrations.RemoveField(
            model_name='accounttemplateitem',
            name='reconciliation_cycle_interval',
        ),
    ]
