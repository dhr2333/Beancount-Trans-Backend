"""标签重复创建校验测试。"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.test import APIRequestFactory

from project.apps.tags.models import Tag
from project.apps.tags.serializers import TagSerializer, _DUPLICATE_TAG_MSG

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username='tagdupuser',
        email='tagdup@example.com',
        password='testpass123',
    )


@pytest.fixture
def auth_request(user):
    factory = APIRequestFactory()
    request = factory.post('/tags/')
    request.user = user
    return request


class TestTagDuplicateValidation:
    def test_create_duplicate_nested_tag_raises_validation_error(self, user, auth_request):
        Tag(name='Property/Discretionary', owner=user).save()

        serializer = TagSerializer(
            data={'name': 'Property/Discretionary'},
            context={'request': auth_request},
        )
        assert not serializer.is_valid()
        assert serializer.errors['name'][0] == _DUPLICATE_TAG_MSG

    def test_create_duplicate_root_tag_raises_validation_error(self, user, auth_request):
        Tag(name='Irregular', owner=user).save()

        serializer = TagSerializer(
            data={'name': 'Irregular'},
            context={'request': auth_request},
        )
        assert not serializer.is_valid()
        assert serializer.errors['name'][0] == _DUPLICATE_TAG_MSG

    def test_create_different_path_with_same_leaf_raises_integrity_error(self, user, auth_request):
        """unique_together 限制同一用户下叶子名不可重复。"""
        Tag(name='Property/Discretionary', owner=user).save()

        serializer = TagSerializer(
            data={'name': 'Income/Discretionary'},
            context={'request': auth_request},
        )
        assert serializer.is_valid()
        with pytest.raises(serializers.ValidationError) as exc_info:
            serializer.save(owner=user)
        assert exc_info.value.detail['name'][0] == _DUPLICATE_TAG_MSG
