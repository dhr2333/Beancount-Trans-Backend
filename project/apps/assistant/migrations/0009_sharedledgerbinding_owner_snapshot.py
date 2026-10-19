from django.db import migrations, models
import django.db.models.deletion


def backfill_owner_snapshots(apps, schema_editor):
    """回填现有绑定的来源用户快照，供令牌删除后继续展示。"""
    SharedLedgerBinding = apps.get_model('assistant', 'SharedLedgerBinding')
    PersonalAccessToken = apps.get_model('authentication', 'PersonalAccessToken')

    token_map = {
        token.id: token
        for token in PersonalAccessToken.objects.select_related('user').all()
    }
    for binding in SharedLedgerBinding.objects.filter(token_id__isnull=False).iterator():
        token = token_map.get(binding.token_id)
        if token is None:
            continue
        binding.owner_user_id = token.user_id
        binding.owner_username = token.user.username
        binding.save(update_fields=['owner_user_id', 'owner_username'])


class Migration(migrations.Migration):

    dependencies = [
        ('assistant', '0008_reset_shared_binding_last_used_at'),
        ('authentication', '0003_personalaccesstoken'),
    ]

    operations = [
        migrations.AddField(
            model_name='sharedledgerbinding',
            name='owner_user_id',
            field=models.PositiveBigIntegerField(
                blank=True,
                help_text='绑定时令牌所属用户的快照，令牌删除后仍可用于展示与去重',
                null=True,
                verbose_name='来源用户 ID',
            ),
        ),
        migrations.AddField(
            model_name='sharedledgerbinding',
            name='owner_username',
            field=models.CharField(
                blank=True,
                default='',
                max_length=150,
                verbose_name='来源用户名',
            ),
        ),
        migrations.AlterField(
            model_name='sharedledgerbinding',
            name='token',
            field=models.ForeignKey(
                blank=True,
                help_text='令牌被删除后置空，绑定保留但不可用',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='ledger_bindings',
                to='authentication.personalaccesstoken',
                verbose_name='访问令牌',
            ),
        ),
        migrations.RunPython(backfill_owner_snapshots, migrations.RunPython.noop),
    ]
