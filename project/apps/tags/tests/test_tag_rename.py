"""标签路径解析与重命名测试。"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory

from project.apps.tags.models import Tag
from project.apps.tags.serializers import TagSerializer

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username='tagtestuser',
        email='tagtest@example.com',
        password='testpass123',
    )


class TestTagPathParsing:
    def test_create_nested_tag_auto_creates_parents(self, user):
        tag = Tag(name='A/B/C', owner=user)
        tag.save()

        assert tag.get_full_path() == 'A/B/C'
        assert tag.name == 'C'
        assert tag.parent.name == 'B'
        assert tag.parent.parent.name == 'A'
        assert tag.parent.parent.parent is None

    def test_create_root_tag(self, user):
        tag = Tag(name='RootOnly', owner=user)
        tag.save()

        assert tag.get_full_path() == 'RootOnly'
        assert tag.parent is None


class TestTagRename:
    def test_edit_without_rename_keeps_path(self, user):
        """编辑时提交完整路径，不应出现 Property/Property/Discretionary。"""
        tag = Tag(name='Property/Discretionary', owner=user)
        tag.save()
        assert tag.get_full_path() == 'Property/Discretionary'

        tag.name = 'Property/Discretionary'
        tag.save()
        tag.refresh_from_db()

        assert tag.get_full_path() == 'Property/Discretionary'
        assert tag.name == 'Discretionary'
        assert tag.parent.name == 'Property'

    def test_rename_leaf(self, user):
        tag = Tag(name='Property/Discretionary', owner=user)
        tag.save()

        tag.name = 'Property/NewLeaf'
        tag.save()
        tag.refresh_from_db()

        assert tag.get_full_path() == 'Property/NewLeaf'
        assert tag.name == 'NewLeaf'

    def test_move_to_different_parent(self, user):
        tag = Tag(name='Property/Discretionary', owner=user)
        tag.save()

        tag.name = 'Income/NewLeaf'
        tag.save()
        tag.refresh_from_db()

        assert tag.get_full_path() == 'Income/NewLeaf'
        assert tag.parent.name == 'Income'
        assert tag.parent.parent is None

    def test_promote_to_root(self, user):
        tag = Tag(name='Property/Discretionary', owner=user)
        tag.save()

        tag.name = 'RootOnly'
        tag.parent = None
        tag.save()
        tag.refresh_from_db()

        assert tag.get_full_path() == 'RootOnly'
        assert tag.parent is None

    def test_promote_to_root_via_serializer_same_leaf_name(self, user):
        """Channel/Offline 改为 Offline 时应提升为根标签，而非保持原路径。"""
        tag = Tag(name='Channel/Offline', owner=user)
        tag.save()

        factory = APIRequestFactory()
        request = factory.patch('/')
        request.user = user

        serializer = TagSerializer(
            instance=tag,
            data={'name': 'Offline'},
            partial=True,
            context={'request': request},
        )
        assert serializer.is_valid(), serializer.errors
        serializer.save()
        tag.refresh_from_db()

        assert tag.get_full_path() == 'Offline'
        assert tag.parent is None


class TestTagEnableIndependent:
    def test_toggle_enable_keeps_path(self, user):
        """仅切换启用状态时不应改变标签路径。"""
        tag = Tag(name='Property/Discretionary', owner=user)
        tag.save()
        parent = tag.parent

        tag.enable = False
        tag.save()
        tag.refresh_from_db()

        assert tag.get_full_path() == 'Property/Discretionary'
        assert tag.parent_id == parent.id
        assert tag.enable is False

        tag.enable = True
        tag.save()
        tag.refresh_from_db()

        assert tag.get_full_path() == 'Property/Discretionary'
        assert tag.parent_id == parent.id

    def test_disable_parent_does_not_affect_children(self, user):
        parent = Tag(name='Property', owner=user, enable=True)
        parent.save()
        child = Tag(name='Discretionary', owner=user, parent=parent, enable=True)
        child.save()

        parent.enable = False
        parent.save()

        child.refresh_from_db()
        assert parent.enable is False
        assert child.enable is True

    def test_enable_child_does_not_affect_ancestors(self, user):
        root = Tag(name='Property', owner=user, enable=False)
        root.save()
        child = Tag(name='Discretionary', owner=user, parent=root, enable=False)
        child.save()

        child.enable = True
        child.save()

        root.refresh_from_db()
        child.refresh_from_db()
        assert child.enable is True
        assert root.enable is False
