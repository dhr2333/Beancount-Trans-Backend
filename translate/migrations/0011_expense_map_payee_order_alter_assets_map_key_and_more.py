# Generated by Django 4.2.1 on 2023-06-07 03:11

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('translate', '0010_alter_assets_map_full'),
    ]

    operations = [
        migrations.AddField(
            model_name='expense_map',
            name='payee_order',
            field=models.IntegerField(default=100),
        ),
        migrations.AlterField(
            model_name='assets_map',
            name='key',
            field=models.CharField(max_length=16, unique=True),
        ),
        migrations.AlterField(
            model_name='expense_map',
            name='key',
            field=models.CharField(max_length=16, unique=True),
        ),
        migrations.AlterField(
            model_name='expense_map',
            name='payee',
            field=models.CharField(max_length=8, null=True),
        ),
    ]