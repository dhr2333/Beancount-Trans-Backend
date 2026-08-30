from django.db import migrations, models


def copy_deepseek_key_to_assistant(apps, schema_editor):
    FormatConfig = apps.get_model('translate', 'FormatConfig')
    for config in FormatConfig.objects.all():
        if (config.deepseek_apikey or '').strip() and not (config.assistant_api_key or '').strip():
            config.assistant_api_key = config.deepseek_apikey
            config.save(update_fields=['assistant_api_key'])


class Migration(migrations.Migration):

    dependencies = [
        ('translate', '0009_alter_formatconfig_income_template_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='formatconfig',
            name='assistant_api_key',
            field=models.CharField(
                blank=True, help_text='账本助手 API 密钥', max_length=256, null=True
            ),
        ),
        migrations.AddField(
            model_name='formatconfig',
            name='assistant_base_url',
            field=models.CharField(
                blank=True, help_text='账本助手 API 接口地址', max_length=256, null=True
            ),
        ),
        migrations.AddField(
            model_name='formatconfig',
            name='assistant_model',
            field=models.CharField(
                blank=True, help_text='账本助手模型名称', max_length=64, null=True
            ),
        ),
        migrations.RunPython(copy_deepseek_key_to_assistant, migrations.RunPython.noop),
    ]
