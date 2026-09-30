from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('assistant', '0006_sharedledgerbinding_aliases'),
    ]

    operations = [
        migrations.AddField(
            model_name='chatmessage',
            name='modes',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='本条回复使用的模式标签，如 normal/plain/insight/bookkeeping',
                verbose_name='应答模式',
            ),
        ),
    ]
