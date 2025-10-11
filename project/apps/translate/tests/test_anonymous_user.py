# project/apps/translate/tests/test_anonymous_user.py
"""
测试匿名用户使用解析功能
验证匿名用户可以访问 admin（id=1）用户的数据
"""
import pytest
from django.contrib.auth import get_user_model
from project.apps.account.models import Account, AccountTemplate
from project.apps.maps.models import Expense, Assets, Income, Template
from project.apps.translate.models import FormatConfig

User = get_user_model()


@pytest.fixture(scope='class')
def setup_admin_user(django_db_blocker):
    """设置 admin 用户和官方模板"""
    with django_db_blocker.unblock():
        # 创建或获取 admin 用户
        admin_user, created = User.objects.get_or_create(
            id=1,
            defaults={
                'username': 'admin',
                'email': 'admin@test.com',
                'is_staff': True,
                'is_superuser': True
            }
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()

        # 应用官方模板
        from project.apps.account.signals import apply_official_account_templates
        from project.apps.maps.signals import apply_official_templates

        # 只在没有数据时应用
        if Account.objects.filter(owner=admin_user).count() == 0:
            apply_official_account_templates(admin_user)

        if Expense.objects.filter(owner=admin_user).count() == 0:
            apply_official_templates(admin_user)

        FormatConfig.get_user_config(admin_user)

        return admin_user


@pytest.mark.django_db
@pytest.mark.usefixtures('setup_admin_user')
class TestAnonymousUserAccess:
    """测试匿名用户访问"""

    def test_admin_user_data_exists(self):
        """测试 admin 用户数据存在"""
        admin_user = User.objects.get(id=1)
        assert admin_user is not None
        assert admin_user.username == 'admin'

        # 检查账户
        accounts = Account.objects.filter(owner=admin_user)
        assert accounts.count() > 0, "admin 用户应该有账户数据"

        # 检查映射
        expenses = Expense.objects.filter(owner=admin_user)
        assets = Assets.objects.filter(owner=admin_user)
        incomes = Income.objects.filter(owner=admin_user)
        assert expenses.count() > 0, "admin 用户应该有支出映射"
        assert assets.count() > 0, "admin 用户应该有资产映射"

        # 检查配置
        config = FormatConfig.objects.filter(owner=admin_user).first()
        assert config is not None, "admin 用户应该有格式化配置"

    def test_anonymous_user_can_access_admin_data(self, client):
        """测试匿名用户可以访问 admin 用户数据"""
        # 获取账户列表（匿名请求）
        response = client.get('/api/account/')
        assert response.status_code == 200

        # 验证返回的是 admin 用户的数据
        data = response.json() if hasattr(response, 'json') else response.data
        if isinstance(data, dict) and data.get('results'):
            first_account = data['results'][0]
            account_obj = Account.objects.get(id=first_account['id'])
            assert account_obj.owner.id == 1, "匿名用户应该访问 admin 用户的数据"
        elif isinstance(data, list) and len(data) > 0:
            first_account = data[0]
            account_obj = Account.objects.get(id=first_account['id'])
            assert account_obj.owner.id == 1, "匿名用户应该访问 admin 用户的数据"

    def test_format_config_for_anonymous_user(self):
        """测试匿名用户获取格式化配置"""
        # 匿名用户调用 get_user_config 应返回 admin 用户的配置
        config = FormatConfig.get_user_config(user=None)
        assert config is not None
        assert config.owner.id == 1

