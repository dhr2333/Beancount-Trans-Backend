from django.db import migrations, models


def copy_alias_to_aliases(apps, schema_editor):
    """把原有的单值 alias 迁移进新的 aliases 列表，保留既有别名。"""
    SharedLedgerBinding = apps.get_model('assistant', 'SharedLedgerBinding')
    for binding in SharedLedgerBinding.objects.all():
        alias = binding.alias or ''
        binding.aliases = [alias] if alias else []
        binding.save(update_fields=['aliases'])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('assistant', '0005_rename_label_sharedledgerbinding_alias'),
    ]

    operations = [
        migrations.AddField(
            model_name='sharedledgerbinding',
            name='aliases',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='Copilot 可用其中任意一个别名识别这个共享账本；可为空，为空时用来源用户名',
                verbose_name='别名',
            ),
        ),
        migrations.RunPython(copy_alias_to_aliases, noop_reverse),
        migrations.RemoveConstraint(
            model_name='sharedledgerbinding',
            name='shared_ledger_binding_recipient_alias_unique',
        ),
        migrations.RemoveField(
            model_name='sharedledgerbinding',
            name='alias',
        ),
    ]
