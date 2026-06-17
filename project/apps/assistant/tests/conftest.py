import os
import tempfile

import pytest
from django.contrib.auth import get_user_model

from project.apps.account.models import Account
from project.apps.tags.models import Tag

User = get_user_model()

SAMPLE_BEAN = """2024-01-01 open Assets:Cash CNY
2024-01-01 open Expenses:Food CNY
2024-01-01 open Income:Salary CNY

2024-01-05 * "午餐" "餐厅"
  Expenses:Food  50.00 CNY
  Assets:Cash  -50.00 CNY

2024-01-10 * "工资"
  Assets:Cash  5000.00 CNY
  Income:Salary  -5000.00 CNY
"""


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username='assistantuser',
        email='assistant@example.com',
        password='testpass123',
    )


@pytest.fixture
def bean_file(tmp_path, settings, user, monkeypatch):
    assets_dir = tmp_path / user.username
    assets_dir.mkdir(parents=True)
    main_bean = assets_dir / 'main.bean'
    main_bean.write_text(SAMPLE_BEAN, encoding='utf-8')
    monkeypatch.setattr(settings, 'ASSETS_BASE_PATH', tmp_path)
    return main_bean


@pytest.fixture
def platform_metadata(user):
    """平台账户与标签描述元数据。"""
    Account.objects.create(
        owner=user,
        account='Expenses:Food',
        description='餐饮',
        enable=True,
    )
    Account.objects.create(
        owner=user,
        account='Assets:Cash',
        description='现金',
        enable=True,
    )
    Tag.objects.create(
        owner=user,
        name='Discretionary',
        description='非必要支出',
        enable=True,
    )
    return user
