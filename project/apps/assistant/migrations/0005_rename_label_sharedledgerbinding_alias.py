from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('assistant', '0004_chatsession_shared_binding_ids_sharedledgerbinding'),
    ]

    operations = [
        migrations.RenameField(
            model_name='sharedledgerbinding',
            old_name='label',
            new_name='alias',
        ),
        migrations.AlterField(
            model_name='sharedledgerbinding',
            name='alias',
            field=models.CharField(
                help_text='Copilot 用该别名识别这个共享账本',
                max_length=64,
                verbose_name='别名',
            ),
        ),
        migrations.AddConstraint(
            model_name='sharedledgerbinding',
            constraint=models.UniqueConstraint(
                fields=('recipient', 'alias'),
                name='shared_ledger_binding_recipient_alias_unique',
            ),
        ),
    ]
