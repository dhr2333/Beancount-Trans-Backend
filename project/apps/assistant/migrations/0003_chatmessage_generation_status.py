from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('assistant', '0002_chat_sessions'),
    ]

    operations = [
        migrations.AddField(
            model_name='chatmessage',
            name='celery_task_id',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='chatmessage',
            name='generation_status',
            field=models.CharField(
                choices=[
                    ('generating', '生成中'),
                    ('complete', '已完成'),
                    ('cancelled', '已取消'),
                    ('failed', '失败'),
                ],
                default='complete',
                max_length=16,
            ),
        ),
    ]
