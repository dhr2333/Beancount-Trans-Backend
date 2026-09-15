from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('git_repository', '0004_alter_gitrepository_provider'),
    ]

    operations = [
        migrations.AddField(
            model_name='gitrepository',
            name='sync_paused',
            field=models.BooleanField(default=False, help_text='是否已取消同步（暂停自动拉取）'),
        ),
    ]
