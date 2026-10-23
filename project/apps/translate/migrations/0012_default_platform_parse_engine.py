from django.db import migrations, models


def migrate_bert_to_platform(apps, schema_editor):
    FormatConfig = apps.get_model('translate', 'FormatConfig')
    # 兼容历史小写值与早期 spaCy 配置
    FormatConfig.objects.filter(ai_model__iexact='bert').update(ai_model='Platform')
    FormatConfig.objects.filter(ai_model__iexact='spacy').update(ai_model='Platform')


class Migration(migrations.Migration):

    dependencies = [
        ('translate', '0011_migrate_spacy_to_bert'),
    ]

    operations = [
        migrations.AlterField(
            model_name='formatconfig',
            name='ai_model',
            field=models.CharField(default='Platform', help_text='AI模型', max_length=16),
        ),
        migrations.RunPython(migrate_bert_to_platform, migrations.RunPython.noop),
    ]
