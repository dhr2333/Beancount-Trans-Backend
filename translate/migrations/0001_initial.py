# Generated by Django 4.2.1 on 2023-07-31 06:18

from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Assets',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('key', models.CharField(help_text='关键字', max_length=16)),
                ('full', models.CharField(help_text='账户名称', max_length=16)),
                ('income', models.CharField(default='Income:Other', help_text='收入账户', max_length=64)),
            ],
            options={
                'verbose_name': '收入映射',
                'verbose_name_plural': '收入映射',
                'db_table': 'maps_assets',
            },
        ),
        migrations.CreateModel(
            name='Expense',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('key', models.CharField(help_text='关键字', max_length=16)),
                ('payee', models.CharField(help_text='商家', max_length=8, null=True)),
                ('payee_order', models.IntegerField(default=100, help_text='优先级')),
                ('expend', models.CharField(default='Expenses:Other', help_text='支出账户', max_length=64)),
                ('tag', models.CharField(help_text='标签', max_length=16)),
                ('classification', models.CharField(help_text='归类', max_length=16)),
            ],
            options={
                'verbose_name': '支出映射',
                'verbose_name_plural': '支出映射',
                'db_table': 'maps_expense',
            },
        ),
    ]
