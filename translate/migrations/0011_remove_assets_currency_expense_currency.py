# Generated by Django 5.1.7 on 2025-03-29 00:45

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('translate', '0010_assets_currency'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='assets',
            name='currency',
        ),
        migrations.AddField(
            model_name='expense',
            name='currency',
            field=models.CharField(help_text='货币', max_length=24, null=True, validators=[django.core.validators.RegexValidator(message="货币必须以大写字母开头，以大写字母/数字结尾，并且只能包含 [A-Z0-9'._-]", regex="^[A-Z][A-Z0-9\\'._-]{0,22}([A-Z0-9])?$")]),
        ),
    ]
