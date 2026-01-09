import pytest
from django.contrib.auth.models import User
from project.apps.authentication.utils import (
    is_valid_username_format,
    generate_unique_username,
    validate_username_format,
    extract_local_phone_number
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

    def test_extract_local_phone_number_e164_format(self):
        """测试从 E164 格式手机号中提取本地号码"""
        # 测试 +86 开头的中国手机号
        result = extract_local_phone_number('+8613800138000')
        assert result == '13800138000'
        
        result = extract_local_phone_number('+8613800138001')
        assert result == '13800138001'

    def test_extract_local_phone_number_without_plus(self):
        """测试不带 + 号的手机号"""
        result = extract_local_phone_number('8613800138002')
        assert result == '13800138002'

    def test_extract_local_phone_number_local_only(self):
        """测试已经是本地号码的情况"""
        result = extract_local_phone_number('13800138003')
        assert result == '13800138003'

    def test_extract_local_phone_number_phone_number_field(self):
        """测试 PhoneNumberField 对象（如果有 national_number 属性）"""
        # 创建一个模拟对象
        class MockPhoneNumber:
            def __init__(self, national_number):
                self.national_number = national_number
        
        mock_phone = MockPhoneNumber('13800138004')
        result = extract_local_phone_number(mock_phone)
        assert result == '13800138004'

    def test_extract_local_phone_number_empty(self):
        """测试空值"""
        assert extract_local_phone_number('') == ''
        assert extract_local_phone_number(None) == ''

    def test_extract_local_phone_number_invalid_format(self):
        """测试无效格式（应该返回所有数字作为备选）"""
        # 如果格式不符合预期，应该返回所有数字
        result = extract_local_phone_number('+1234567890')
        assert result.isdigit()  # 应该返回数字字符串

