"""MCP 应用测试共用夹具。

注意：mcp SDK 会把同步的工具/资源/提示词函数放到工作线程执行（anyio.to_thread），
而 pytest-django 默认用事务包裹测试，SQLite 共享缓存内存库会因此报
「database table is locked」。故本目录的测试统一使用
``pytest.mark.django_db(transaction=True)``。
"""
import pytest
from django.contrib.auth import get_user_model

from project.apps.account.models import Account
from project.apps.mcp.server import create_server
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

NESTED_BEAN = """2024-02-01 * "咖啡"
  Expenses:Food  30.00 CNY
  Assets:Cash  -30.00 CNY
"""

OTHER_BEAN = """2024-01-01 open Assets:Cash CNY
2024-01-01 open Expenses:Rent CNY

2024-03-01 * "房租"
  Expenses:Rent  2000.00 CNY
  Assets:Cash  -2000.00 CNY
"""


@pytest.fixture
def assets_base(tmp_path, settings, monkeypatch):
    """把账本根目录指向临时目录。

    必须在创建用户之前生效：User 的 post_save 信号会按 ASSETS_BASE_PATH
    初始化用户账本目录，否则会在仓库内的 Assets 下产生垃圾目录。
    """
    monkeypatch.setattr(settings, 'ASSETS_BASE_PATH', tmp_path)
    (tmp_path / 'outside.bean').write_text('outside', encoding='utf-8')
    return tmp_path


@pytest.fixture
def user(assets_base):
    return User.objects.create_user(
        username='mcpuser',
        email='mcp@example.com',
        password='testpass123',
    )


@pytest.fixture
def other_user(assets_base):
    return User.objects.create_user(username='otheruser', password='testpass123')


@pytest.fixture
def assets_root(assets_base, user):
    """用户资产根目录（信号已按 ASSETS_BASE_PATH 建好，这里只做幂等保证）。"""
    root = assets_base / user.username
    root.mkdir(parents=True, exist_ok=True)
    return root


@pytest.fixture
def ledger_files(assets_root):
    """main.bean + 子目录 .bean + 非账本文件。"""
    main = assets_root / 'main.bean'
    main.write_text(SAMPLE_BEAN, encoding='utf-8')
    nested_dir = assets_root / '2024'
    nested_dir.mkdir()
    nested = nested_dir / '01.bean'
    nested.write_text(NESTED_BEAN, encoding='utf-8')
    notes = assets_root / 'notes.txt'
    notes.write_text('not a ledger', encoding='utf-8')
    return {'main': main, 'nested': nested, 'notes': notes, 'root': assets_root}


@pytest.fixture
def other_assets(assets_base, other_user):
    """另一个用户的资产目录，用于验证多用户隔离。"""
    root = assets_base / other_user.username
    root.mkdir(parents=True, exist_ok=True)
    (root / 'main.bean').write_text(OTHER_BEAN, encoding='utf-8')
    return root


@pytest.fixture
def platform_metadata(user):
    Account.objects.create(owner=user, account='Expenses:Food', description='餐饮', enable=True)
    Account.objects.create(owner=user, account='Assets:Cash', description='现金', enable=True)
    Tag.objects.create(owner=user, name='Discretionary', description='非必要支出', enable=True)
    return user


@pytest.fixture
def mcp_server(settings, monkeypatch, user):
    """关闭鉴权、以 MCP_DEV_USERNAME 指认当前用户的 MCP 服务实例。"""
    monkeypatch.setattr(settings, 'MCP_DEV_USERNAME', user.username)
    monkeypatch.setattr(settings, 'MCP_AUTH_ENABLED', False)
    return create_server()
