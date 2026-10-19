from django.db import migrations


def reset_last_used_at(apps, schema_editor):
    """旧逻辑在“仅纳入请求”时就会写入 last_used_at，清空以等待真实查询重新记录。"""
    SharedLedgerBinding = apps.get_model('assistant', 'SharedLedgerBinding')
    SharedLedgerBinding.objects.filter(last_used_at__isnull=False).update(last_used_at=None)


class Migration(migrations.Migration):

    dependencies = [
        ('assistant', '0007_chatmessage_modes'),
    ]

    operations = [
        migrations.RunPython(reset_last_used_at, migrations.RunPython.noop),
    ]
