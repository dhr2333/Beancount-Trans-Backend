# Generated by Django 5.1.7 on 2025-03-27 08:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('translate', '0006_formatconfig'),
    ]

    operations = [
        migrations.AddField(
            model_name='formatconfig',
            name='commission_template',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
    ]
