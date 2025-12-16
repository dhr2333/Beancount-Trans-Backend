import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError

from ..models import GitRepository

User = get_user_model()


@pytest.mark.django_db
class TestGitRepositoryModel:
    """Git 仓库模型测试"""
    
    def test_create_git_repository(self):
        """测试创建 Git 仓库"""
        user = User.objects.create_user(username='testuser', password='testpass')
        
        repo = GitRepository.objects.create(
            owner=user,
            repo_name='abc123-assets',
            gitea_repo_id=123,
            deploy_key_private='private_key_content',
            deploy_key_public='public_key_content'
        )
        
        assert repo.owner == user
        assert repo.repo_name == 'abc123-assets'  # 修正期望值与实际创建的一致
        assert repo.sync_status == 'pending'  # 默认状态
        assert repo.created_with_template is True  # 默认值
    
    def test_one_to_one_relationship(self):
        """测试用户和仓库的一对一关系"""
        user = User.objects.create_user(username='testuser', password='testpass')
        
        # 创建第一个仓库
        GitRepository.objects.create(
            owner=user,
            repo_name='abc123-assets',
            gitea_repo_id=123,
            deploy_key_private='private_key_content',
            deploy_key_public='public_key_content'
        )
        
        # 尝试为同一用户创建第二个仓库，应该失败
        with pytest.raises(IntegrityError):
            GitRepository.objects.create(
                owner=user,
                repo_name='def456-assets',
                gitea_repo_id=124,
                deploy_key_private='private_key_content_2',
                deploy_key_public='public_key_content_2'
            )
    
    def test_str_method(self):
        """测试字符串表示方法"""
        user = User.objects.create_user(username='testuser', password='testpass')
        
        repo = GitRepository.objects.create(
            owner=user,
            repo_name='abc123-assets',
            gitea_repo_id=123,
            deploy_key_private='private_key_content',
            deploy_key_public='public_key_content'
        )
        
        assert str(repo) == 'testuser - abc123-assets'
    
    def test_ssh_clone_url_property(self):
        """测试 SSH clone URL 属性"""
        user = User.objects.create_user(username='testuser', password='testpass')
        
        repo = GitRepository.objects.create(
            owner=user,
            repo_name='abc123-assets',
            gitea_repo_id=123,
            deploy_key_private='private_key_content',
            deploy_key_public='public_key_content'
        )
        
        expected_ssh_url = 'ssh://git@gitea.dhr2333.cn:30022/beancount-trans/abc123-assets.git'
        assert repo.ssh_clone_url == expected_ssh_url
    
    # HTTPS clone URL 属性已移除，因为 repo_url 字段不再存在
    
    def test_sync_status_choices(self):
        """测试同步状态选择"""
        user = User.objects.create_user(username='testuser', password='testpass')
        
        # 测试所有有效的同步状态
        valid_statuses = ['pending', 'syncing', 'success', 'failed']
        
        for status in valid_statuses:
            repo = GitRepository.objects.create(
                owner=user,
                repo_name=f'test{len(status)}-assets',
                gitea_repo_id=123 + len(status),
                deploy_key_private='private_key_content',
                deploy_key_public='public_key_content',
                sync_status=status
            )
            
            assert repo.sync_status == status
            
            # 清理以避免重复约束错误
            repo.delete()
    
    def test_base_model_fields(self):
        """测试基础模型字段（created, modified）"""
        user = User.objects.create_user(username='testuser', password='testpass')
        
        repo = GitRepository.objects.create(
            owner=user,
            repo_name='abc123-assets',
            gitea_repo_id=123,
            deploy_key_private='private_key_content',
            deploy_key_public='public_key_content'
        )
        
        # 验证 created 和 modified 字段存在
        assert repo.created is not None
        assert repo.modified is not None
        # 允许微秒级的时间差异（在快速执行的测试环境中可能存在）
        time_diff = abs((repo.created - repo.modified).total_seconds())
        assert time_diff < 1  # 允许1秒内的差异
    
    def test_optional_fields(self):
        """测试可选字段"""
        user = User.objects.create_user(username='testuser', password='testpass')
        
        repo = GitRepository.objects.create(
            owner=user,
            repo_name='abc123-assets',
            gitea_repo_id=123,
            deploy_key_private='private_key_content',
            deploy_key_public='public_key_content'
            # deploy_key_id, last_sync_at, sync_error 为可选字段
        )
        
        assert repo.deploy_key_id is None
        assert repo.last_sync_at is None
        assert repo.sync_error == ''  # 默认空字符串

