# Generated manually for tags app

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Tag',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, help_text='创建时间', verbose_name='创建时间')),
                ('modified', models.DateTimeField(auto_now=True, help_text='修改时间', verbose_name='修改时间')),
                ('name', models.CharField(help_text='标签名称', max_length=64)),
                ('description', models.TextField(blank=True, help_text='标签描述')),
                ('enable', models.BooleanField(default=True, help_text='是否启用')),
                ('owner', models.ForeignKey(db_index=True, on_delete=django.db.models.deletion.CASCADE, related_name='tags', to=settings.AUTH_USER_MODEL)),
                ('parent', models.ForeignKey(blank=True, help_text='父标签', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='children', to='tags.tag')),
            ],
            options={
                'verbose_name': '标签',
                'verbose_name_plural': '标签',
                'db_table': 'tags_tag',
                'ordering': ['name'],
                'unique_together': {('name', 'owner')},
            },
        ),
    ]

