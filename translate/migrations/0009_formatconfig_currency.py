# Generated by Django 5.1.7 on 2025-03-28 02:25

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('translate', '0008_alter_formatconfig_commission_template_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='formatconfig',
            name='currency',
            field=models.CharField(default='CNY', max_length=24, validators=[django.core.validators.RegexValidator(message="货币必须以大写字母开头，以大写字母/数字结尾，并且只能包含 [A-Z0-9'._-]", regex="^[A-Z][A-Z0-9\\'._-]{0,22}([A-Z0-9])?$")]),
        ),
    ]
