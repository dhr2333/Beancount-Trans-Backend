"""支出映射模板标签应用测试。"""
import pytest
from django.contrib.auth import get_user_model

from project.apps.account.models import Account
from project.apps.maps.models import Expense, Template, TemplateItem
from project.apps.maps.signals import apply_official_templates
from project.apps.tags.models import Tag, TagTemplate, TagTemplateItem
from project.apps.tags.signals import apply_official_tag_templates

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username='maptaguser',
        email='maptag@example.com',
        password='testpass123',
    )


@pytest.fixture
def expense_template(db, user):
    template = Template.objects.create(
        name='官方支出映射',
        type='expense',
        is_official=True,
        owner=user,
    )
    TemplateItem.objects.create(
        template=template,
        key='财政局',
        account='Expenses:Finance:Fine',
        tag_paths=['Emergency'],
    )
    TemplateItem.objects.create(
        template=template,
        key='车险',
        account='Expenses:Finance:Insurance',
        tag_paths=['Fixed', 'Online'],
    )
    return template


class TestExpenseTemplateTags:
    def test_apply_expense_template_sets_tags(self, user, expense_template):
        Account.objects.create(owner=user, account='Expenses:Finance:Fine')
        Account.objects.create(owner=user, account='Expenses:Finance:Insurance')
        Tag(name='Emergency', owner=user).save()
        Tag(name='Fixed', owner=user).save()
        Tag(name='Online', owner=user).save()

        apply_official_templates(user)

        finance_bureau = Expense.objects.get(owner=user, key='财政局')
        car_insurance = Expense.objects.get(owner=user, key='车险')

        assert set(finance_bureau.tags.values_list('name', flat=True)) == {'Emergency'}
        assert set(car_insurance.tags.values_list('name', flat=True)) == {'Fixed', 'Online'}

    def test_tags_applied_after_official_tag_templates(self, user, expense_template):
        Account.objects.create(owner=user, account='Expenses:Finance:Fine')
        Account.objects.create(owner=user, account='Expenses:Finance:Insurance')

        tag_template = TagTemplate.objects.create(
            name='官方标签模板',
            is_official=True,
            owner=user,
        )
        for tag_path in ('Emergency', 'Fixed', 'Online'):
            TagTemplateItem.objects.create(template=tag_template, tag_path=tag_path)

        apply_official_tag_templates(user)
        apply_official_templates(user)

        finance_bureau = Expense.objects.get(owner=user, key='财政局')
        car_insurance = Expense.objects.get(owner=user, key='车险')

        assert finance_bureau.tags.filter(name='Emergency').exists()
        assert car_insurance.tags.filter(name='Fixed').exists()
        assert car_insurance.tags.filter(name='Online').exists()
