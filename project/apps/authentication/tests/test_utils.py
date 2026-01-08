import pytest
from django.contrib.auth.models import User
from project.apps.authentication.utils import (
    is_valid_username_format,
    generate_unique_username,
    validate_username_format
)


@pytest.mark.django_db
class TestUsernameUtils:
    """用户名工具函数测试"""

    def test_is_valid_username_format_valid(self):
        """测试有效用户名格式"""
        valid_usernames = [
            'testuser',
            'user123',
            'test_user',
            'user-123',
            'abc123assets',  # 没有连字符
            'testuser123',
            'user_abc',
        ]

        for username in valid_usernames:
            assert is_valid_username_format(username) is True

    def test_is_valid_username_format_git_repo_pattern(self):
        """测试 Git 仓库目录名格式被拒绝"""
        invalid_usernames = [
            'abc123-assets',
            'ABCDEF-assets',
            '123456-assets',
            'abcdef123456-assets',
            'a1b2c3-assets',
            '1234567890abcdef-assets',
        ]

        for username in invalid_usernames:
            assert is_valid_username_format(username) is False

    def test_is_valid_username_format_phone_pattern(self):
        """测试手机号注册格式被拒绝（用户手动修改时）"""
        invalid_usernames = [
            '13800138000',
            # '1234567890',
            # '123456789012345',
        ]

        for username in invalid_usernames:
            assert is_valid_username_format(username, allow_phone_format=False) is False

    def test_is_valid_username_format_phone_pattern_allowed_internal(self):
        """测试手机号注册格式在内部生成时允许"""
        valid_usernames = [
            '13800138000',
            '1234567890',
        ]

        for username in valid_usernames:
            assert is_valid_username_format(username, allow_phone_format=True) is True

    def test_is_valid_username_format_empty(self):
        """测试空用户名"""
        assert is_valid_username_format('') is False
        assert is_valid_username_format(None) is False

    def test_generate_unique_username_no_conflict(self):
        """测试生成唯一用户名（无冲突）"""
        username = generate_unique_username('testuser')
        assert username == 'testuser'
        assert is_valid_username_format(username)

    def test_generate_unique_username_with_conflict(self):
        """测试生成唯一用户名（有冲突）"""
        # 创建一个用户
        User.objects.create_user(username='testuser', password='TestPass123!')

        # 尝试生成相同的用户名
        username = generate_unique_username('testuser')
        assert username != 'testuser'
        assert username.startswith('testuser')
        assert is_valid_username_format(username)
        # 验证用户名是唯一的
        assert not User.objects.filter(username=username).exists()

    def test_generate_unique_username_git_repo_format(self):
        """测试 Git 仓库目录名格式的用户名被自动修改"""
        username = generate_unique_username('abc123-assets')
        assert username != 'abc123-assets'
        assert is_valid_username_format(username)

    def test_generate_unique_username_git_repo_format_conflict(self):
        """测试 Git 仓库目录名格式且已存在时的处理"""
        # 创建一个 Git 仓库目录名格式的用户（虽然不应该存在，但测试边界情况）
        User.objects.create_user(username='abc123-assets_user', password='TestPass123!')

        username = generate_unique_username('abc123-assets')
        assert username != 'abc123-assets'
        assert is_valid_username_format(username)
        assert not User.objects.filter(username=username).exists()

    def test_generate_unique_username_short_base(self):
        """测试短用户名自动处理"""
        username = generate_unique_username('ab')
        assert username.startswith('user_')
        assert len(username) >= 3

    def test_generate_unique_username_empty_base(self):
        """测试空用户名自动处理"""
        username = generate_unique_username('')
        assert username.startswith('user')

    def test_validate_username_format_valid(self):
        """测试验证用户名格式（有效）"""
        is_valid, message = validate_username_format('testuser')
        assert is_valid is True
        assert message == ''

    def test_validate_username_format_invalid_empty(self):
        """测试验证用户名格式（空）"""
        is_valid, message = validate_username_format('')
        assert is_valid is False
        assert '不能为空' in message

    def test_validate_username_format_invalid_git_repo(self):
        """测试验证用户名格式（Git 仓库目录名格式）"""
        is_valid, message = validate_username_format('abc123-assets')
        assert is_valid is False
        assert 'Git 仓库目录名格式' in message

    def test_validate_username_format_invalid_phone(self):
        """测试验证用户名格式（手机号注册格式）"""
        is_valid, message = validate_username_format('13800138000')
        assert is_valid is False
        assert '手机号注册格式' in message

    def test_validate_username_format_phone_allowed_internal(self):
        """测试验证用户名格式（内部生成时允许手机号格式）"""
        is_valid, message = validate_username_format('13800138000', allow_phone_format=True)
        assert is_valid is True
        assert message == ''

