from django.db import migrations


def migrate_spacy_to_bert(apps, schema_editor):
    FormatConfig = apps.get_model('translate', 'FormatConfig')
    FormatConfig.objects.filter(ai_model='spaCy').update(ai_model='BERT')


class Migration(migrations.Migration):

    dependencies = [
        ('translate', '0010_formatconfig_assistant_provider'),
    ]

    operations = [
        migrations.RunPython(migrate_spacy_to_bert, migrations.RunPython.noop),
    ]
