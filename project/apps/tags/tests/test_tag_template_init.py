"""官方标签模板应用测试。"""
import pytest
from django.contrib.auth import get_user_model

from project.apps.tags.models import Tag, TagTemplate, TagTemplateItem
from project.apps.tags.signals import apply_official_tag_templates, tag_exists_for_user

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username='taginituser',
        email='taginit@example.com',
        password='testpass123',
    )


@pytest.fixture
def official_tag_template(db, user):
    template = TagTemplate.objects.create(
        name='官方标签模板',
        description='测试用官方标签',
        is_public=True,
        is_official=True,
        owner=user,
    )
    TagTemplateItem.objects.create(
        template=template,
        tag_path='Irregular',
        description='非常规',
        enable=True,
    )
    TagTemplateItem.objects.create(
        template=template,
        tag_path='Property/Discretionary',
        description='资产性支出',
        enable=True,
    )
    return template


class TestApplyOfficialTagTemplates:
    def test_creates_tags_from_official_template(self, user, official_tag_template):
        created = apply_official_tag_templates(user)

        assert created == 2
        assert Tag.objects.filter(owner=user).count() == 3
        assert tag_exists_for_user(user, 'Irregular')
        assert tag_exists_for_user(user, 'Property/Discretionary')
        assert tag_exists_for_user(user, 'Property')

        irregular = Tag.objects.get(owner=user, name='Irregular', parent__isnull=True)
        assert irregular.get_full_path() == 'Irregular'
        assert irregular.enable is True
        assert irregular.description == '非常规'

        discretionary = Tag.objects.get(owner=user, name='Discretionary')
        assert discretionary.get_full_path() == 'Property/Discretionary'
        assert discretionary.description == '资产性支出'

    def test_idempotent_skip_existing_tags(self, user, official_tag_template):
        first_created = apply_official_tag_templates(user)
        second_created = apply_official_tag_templates(user)

        assert first_created == 2
        assert second_created == 0
        assert Tag.objects.filter(owner=user).count() == 3

    def test_nested_path_creates_parent_tags(self, user, official_tag_template):
        apply_official_tag_templates(user)

        property_tag = Tag.objects.get(owner=user, name='Property', parent__isnull=True)
        assert property_tag.enable is True
        assert property_tag.get_full_path() == 'Property'
