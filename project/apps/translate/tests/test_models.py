# tests/test_models.py
from django.test import TestCase
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from maps.models import Expense, Assets, Income

class BaseModelTestMixin:
    """测试模型公共基类的共享逻辑"""
    @classmethod
    def setUpTestData(cls):
        # 创建测试用户
        cls.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )

class ExpenseModelTest(BaseModelTestMixin, TestCase):
    def test_expense_creation(self):
        """测试支出映射模型基础功能"""
        expense = Expense.objects.create(
            key="food",
            payee="超市",
            expend="Expenses:Groceries",
            owner=self.user
        )

        # 基础字段验证
        self.assertEqual(expense.key, "food")
        self.assertEqual(expense.payee, "超市")
        self.assertEqual(expense.expend, "Expenses:Groceries")
        self.assertEqual(expense.owner.username, "testuser")

        # 测试默认值
        expense_with_default = Expense.objects.create(
            key="default_test",
            owner=self.user
        )
        self.assertEqual(expense_with_default.expend, "Expenses:Other")

    def test_required_fields(self):
        """测试必填字段验证"""
        with self.assertRaises(ValidationError):
            obj = Expense(key=None, owner=self.user)
            obj.full_clean()  # 触发完整验证

    def test_meta_options(self):
        """验证模型元数据配置"""
        self.assertEqual(Expense._meta.db_table, 'maps_expense')
        self.assertEqual(Expense._meta.verbose_name, '支出映射')
        self.assertEqual(Expense._meta.verbose_name_plural, '支出映射')

    def test_string_representation(self):
        """测试字符串表示"""
        obj = Expense.objects.create(key="test_str", owner=self.user)
        self.assertEqual(str(obj), "test_str")

    def test_owner_relationship(self):
        """验证用户关联关系"""
        expense = Expense.objects.create(key="relation_test", owner=self.user)
        self.assertIn(expense, self.user.expense.all())

class AssetsModelTest(BaseModelTestMixin, TestCase):
    def test_assets_creation(self):
        """测试资产映射模型"""
        asset = Assets.objects.create(
            key="alipay",
            full="支付宝",
            assets="Assets:Digital:Alipay",
            owner=self.user
        )

        self.assertEqual(asset.key, "alipay")
        self.assertEqual(asset.full, "支付宝")
        self.assertEqual(asset.assets, "Assets:Digital:Alipay")

        # 测试默认值
        asset_default = Assets.objects.create(
            key="default_asset",
            full="默认资产",
            owner=self.user
        )
        self.assertEqual(asset_default.assets, "Assets:Other:Test")

    def test_max_length_constraints(self):
        """测试字段最大长度"""
        with self.assertRaises(ValidationError):
            obj = Assets(
                key="a"*17,  # 超过 max_length=16
                full="test",
                owner=self.user
            )
            obj.full_clean()

class IncomeModelTest(BaseModelTestMixin, TestCase):
    def test_income_creation(self):
        """测试收入映射模型"""
        income = Income.objects.create(
            key="salary",
            payer="公司",
            income="Income:Salary",
            owner=self.user
        )

        self.assertEqual(income.key, "salary")
        self.assertEqual(income.payer, "公司")
        self.assertEqual(income.income, "Income:Salary")

    def test_nullable_field(self):
        """测试可为空字段"""
        income = Income.objects.create(
            key="null_test",
            income="Income:Other",
            owner=self.user
        )
        self.assertIsNone(income.payer)
