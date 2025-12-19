"""
Git 仓库集成测试
测试完整的 Git 仓库创建和模板初始化流程
"""

import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model

from ..services import PlatformGitService, GitServiceException
from ..models import GitRepository
from ..template_service import TemplateServiceException

User = get_user_model()


# class TestGitRepositoryIntegration(TestCase):
#     """Git 仓库集成测试"""

#     def setUp(self):
#         self.test_user = User.objects.create_user(
#             username='testuser',
#             email='test@example.com'
#         )
#         self.git_service = PlatformGitService()

#     def tearDown(self):
#         # 清理测试数据
#         GitRepository.objects.filter(owner=self.test_user).delete()

#     @patch('project.apps.git_repository.services.PlatformGitService._push_template_to_repository')
#     @patch('project.apps.git_repository.services.PlatformGitService._sync_template_to_local')
#     @patch('project.apps.git_repository.template_service.GitHubTemplateService.fetch_template_content')
#     @patch('project.apps.git_repository.clients.GiteaAPIClient.create_repository')
#     @patch('project.apps.git_repository.clients.GiteaAPIClient.add_deploy_key')
#     def test_create_repository_with_template_success(self, mock_add_deploy_key, mock_create_repo, 
#                                                    mock_fetch_template, mock_sync_local, mock_push_template):
#         """测试成功创建基于模板的仓库"""
#         # Mock Gitea API 响应
#         mock_create_repo.return_value = {'id': 123, 'name': 'test-assets'}
#         mock_add_deploy_key.return_value = {'id': 456}

#         # Mock 模板获取
#         temp_dir = Path(tempfile.mkdtemp())
#         try:
#             # 创建模拟模板文件
#             (temp_dir / 'main.bean').write_text('option "title" "xxx的账本"')
#             (temp_dir / 'account').mkdir()
#             (temp_dir / 'account' / 'assets.bean').write_text('1970-01-01 open Assets:Test')

#             mock_fetch_template.return_value = temp_dir

#             # 执行创建仓库
#             git_repo = self.git_service.create_user_repository(
#                 user=self.test_user, 
#                 use_template=True
#             )

#             # 验证数据库记录
#             self.assertIsInstance(git_repo, GitRepository)
#             self.assertEqual(git_repo.owner, self.test_user)
#             self.assertEqual(git_repo.gitea_repo_id, 123)
#             self.assertTrue(git_repo.created_with_template)
#             self.assertEqual(git_repo.deploy_key_id, 456)

#             # 验证调用了模板相关方法
#             mock_fetch_template.assert_called_once()
#             mock_push_template.assert_called_once()
#             mock_sync_local.assert_called_once()

#         finally:
#             shutil.rmtree(temp_dir, ignore_errors=True)

#     @patch('project.apps.git_repository.template_service.GitHubTemplateService.fetch_template_content')
#     @patch('project.apps.git_repository.clients.GiteaAPIClient.create_repository')
#     @patch('project.apps.git_repository.clients.GiteaAPIClient.add_deploy_key')
#     def test_create_repository_template_fetch_failure(self, mock_add_deploy_key, mock_create_repo, mock_fetch_template):
#         """测试模板获取失败的情况"""
#         # Mock Gitea API 响应
#         mock_create_repo.return_value = {'id': 123, 'name': 'test-assets'}
#         mock_add_deploy_key.return_value = {'id': 456}

#         # Mock 模板获取失败
#         mock_fetch_template.side_effect = TemplateServiceException("GitHub API 访问受限")

#         # 执行创建仓库，应该失败
#         with self.assertRaises(GitServiceException) as cm:
#             self.git_service.create_user_repository(
#                 user=self.test_user, 
#                 use_template=True
#             )

#         self.assertIn('模板初始化失败', str(cm.exception))

#         # 验证没有创建数据库记录
#         self.assertFalse(GitRepository.objects.filter(owner=self.test_user).exists())

#     @patch('project.apps.git_repository.clients.GiteaAPIClient.create_repository')
#     @patch('project.apps.git_repository.clients.GiteaAPIClient.add_deploy_key')
#     def test_create_repository_without_template(self, mock_add_deploy_key, mock_create_repo):
#         """测试创建不基于模板的空仓库"""
#         # Mock Gitea API 响应
#         mock_create_repo.return_value = {'id': 123, 'name': 'test-assets'}
#         mock_add_deploy_key.return_value = {'id': 456}

#         # 执行创建仓库
#         git_repo = self.git_service.create_user_repository(
#             user=self.test_user, 
#             use_template=False
#         )

#         # 验证数据库记录
#         self.assertIsInstance(git_repo, GitRepository)
#         self.assertEqual(git_repo.owner, self.test_user)
#         self.assertFalse(git_repo.created_with_template)

#     def test_create_repository_user_already_has_repo(self):
#         """测试用户已有仓库的情况"""
#         # 先创建一个仓库记录
#         GitRepository.objects.create(
#             owner=self.test_user,
#             repo_name='existing-repo',
#             gitea_repo_id=999,
#             deploy_key_private='test-private-key',
#             deploy_key_public='test-public-key'
#         )

#         # 尝试再次创建，应该失败
#         with self.assertRaises(GitServiceException) as cm:
#             self.git_service.create_user_repository(
#                 user=self.test_user, 
#                 use_template=True
#             )

#         self.assertIn('用户已有 Git 仓库', str(cm.exception))


class TestTemplateCustomization(TestCase):
    """模板定制测试"""

    def setUp(self):
        self.test_user = User.objects.create_user(
            username='张三',  # 使用中文用户名测试
            email='zhangsan@example.com'
        )

    def test_customize_template_chinese_username(self):
        """测试中文用户名的模板定制"""
        from ..template_service import GitHubTemplateService

        service = GitHubTemplateService()
        temp_dir = Path(tempfile.mkdtemp())

        try:
            # 创建模拟的 main.bean 文件
            main_bean_content = '''option "title" "xxx的账本"
option "operating_currency" "CNY"

2022-01-01 custom "fava-option" "language" "zh_CN"
'''
            (temp_dir / 'main.bean').write_text(main_bean_content, encoding='utf-8')

            # 执行定制
            service.customize_template_for_user(temp_dir, self.test_user)

            # 验证结果
            customized_content = (temp_dir / 'main.bean').read_text(encoding='utf-8')
            self.assertIn('option "title" "张三的账本"', customized_content)
            self.assertNotIn('option "title" "xxx的账本"', customized_content)

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_customize_template_no_title_found(self):
        """测试模板中没有标题配置的情况"""
        from ..template_service import GitHubTemplateService

        service = GitHubTemplateService()
        temp_dir = Path(tempfile.mkdtemp())

        try:
            # 创建没有标题的 main.bean 文件
            main_bean_content = '''option "operating_currency" "CNY"

2022-01-01 custom "fava-option" "language" "zh_CN"
'''
            (temp_dir / 'main.bean').write_text(main_bean_content, encoding='utf-8')

            # 执行定制（应该不会报错，只是跳过替换）
            service.customize_template_for_user(temp_dir, self.test_user)

            # 验证内容没有变化
            customized_content = (temp_dir / 'main.bean').read_text(encoding='utf-8')
            self.assertEqual(customized_content, main_bean_content)

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


# class TestErrorHandlingAndRollback(TestCase):
#     """错误处理和回滚测试"""

#     def setUp(self):
#         self.test_user = User.objects.create_user(
#             username='testuser',
#             email='test@example.com'
#         )
#         self.git_service = PlatformGitService()

#     @patch('project.apps.git_repository.clients.GiteaAPIClient.delete_repository')
#     @patch('project.apps.git_repository.services.PlatformGitService._push_template_to_repository')
#     @patch('project.apps.git_repository.template_service.GitHubTemplateService.fetch_template_content')
#     @patch('project.apps.git_repository.clients.GiteaAPIClient.create_repository')
#     @patch('project.apps.git_repository.clients.GiteaAPIClient.add_deploy_key')
#     def test_rollback_on_template_push_failure(self, mock_add_deploy_key, mock_create_repo, 
#                                              mock_fetch_template, mock_push_template, mock_delete_repo):
#         """测试模板推送失败时的回滚"""
#         # Mock Gitea API 响应
#         mock_create_repo.return_value = {'id': 123, 'name': 'test-assets'}
#         mock_add_deploy_key.return_value = {'id': 456}

#         # Mock 模板获取成功
#         temp_dir = Path(tempfile.mkdtemp())
#         try:
#             (temp_dir / 'main.bean').write_text('test content')
#             mock_fetch_template.return_value = temp_dir

#             # Mock 推送失败
#             mock_push_template.side_effect = Exception("Git push failed")

#             # 执行创建仓库，应该失败
#             with self.assertRaises(GitServiceException):
#                 self.git_service.create_user_repository(
#                     user=self.test_user, 
#                     use_template=True
#                 )

#             # 验证调用了删除仓库（回滚）
#             mock_delete_repo.assert_called_once()

#             # 验证没有创建数据库记录
#             self.assertFalse(GitRepository.objects.filter(owner=self.test_user).exists())

#         finally:
#             shutil.rmtree(temp_dir, ignore_errors=True)
