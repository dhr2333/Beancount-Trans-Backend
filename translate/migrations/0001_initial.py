# Generated by Django 4.2.1 on 2023-07-04 02:42

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Assets_Map',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(max_length=16, unique=True)),
                ('full', models.CharField(max_length=16)),
                ('income', models.CharField(default='Income:Other', max_length=64)),
            ],
        ),
        migrations.CreateModel(
            name='Expense_Map',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(help_text='关键字', max_length=16, unique=True)),
                ('payee', models.CharField(max_length=8, null=True)),
                ('payee_order', models.IntegerField(default=100)),
                ('expend', models.CharField(default='Expenses:Other', max_length=64)),
                ('tag', models.CharField(max_length=16)),
                ('classification', models.CharField(max_length=16)),
            ],
            options={
                'verbose_name': '支出映射',
                'verbose_name_plural': '支出映射',
                'db_table': 'translate_expense_map',
            },
        ),
    ]
