import pytest
from unittest.mock import patch, MagicMock, mock_open
from django.contrib.auth import get_user_model

from ..services import PlatformGitService, GitServiceException
from ..models import GitRepository

User = get_user_model()


@pytest.mark.django_db
class TestPlatformGitService:
    """平台 Git 服务测试"""
    
    def setup_method(self):
        """测试设置"""
        self.service = PlatformGitService()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass'
        )
    
    @patch('project.apps.git_repository.services.GiteaAPIClient')
    def test_generate_ssh_key_pair(self, mock_gitea_client):
        """测试 SSH 密钥对生成"""
        private_key, public_key = self.service._generate_ssh_key_pair()
        
        assert isinstance(private_key, str)
        assert isinstance(public_key, str)
        assert private_key.startswith('-----BEGIN PRIVATE KEY-----')
        assert 'ssh-rsa' in public_key or 'ssh-ed25519' in public_key
    
    @patch('project.apps.git_repository.services.GiteaAPIClient')
    def test_create_user_repository_success(self, mock_gitea_client):
        """测试成功创建用户仓库"""
        # 模拟 Gitea API 响应
        mock_client = MagicMock()
        mock_gitea_client.return_value = mock_client
        
        mock_client.create_repository.return_value = {
            'id': 123,
            'clone_url': 'https://gitea.dhr2333.cn/beancount-trans/1-beancount.git'
        }
        mock_client.add_deploy_key.return_value = {
            'id': 456,
            'title': 'Platform Deploy Key - testuser'
        }
        
        # 模拟 SSH 密钥生成
        with patch.object(self.service, '_generate_ssh_key_pair') as mock_keygen:
            mock_keygen.return_value = ('private_key', 'public_key')
            
            repo = self.service.create_user_repository(self.user, use_template=True)
        
        assert isinstance(repo, GitRepository)
        assert repo.owner == self.user
        assert repo.repo_name == '1-beancount'
        assert repo.gitea_repo_id == 123
        assert repo.deploy_key_id == 456
        assert repo.created_with_template is True
    
    @patch('project.apps.git_repository.services.GiteaAPIClient')
    def test_create_user_repository_already_exists(self, mock_gitea_client):
        """测试用户已有仓库时的错误处理"""
        # 先创建一个仓库
        GitRepository.objects.create(
            owner=self.user,
            repo_url='https://gitea.dhr2333.cn/beancount-trans/1-beancount.git',
            repo_name='1-beancount',
            gitea_repo_id=123,
            deploy_key_private='private_key',
            deploy_key_public='public_key'
        )
        
        # 尝试再次创建应该失败
        with pytest.raises(GitServiceException, match="用户已有 Git 仓库"):
            self.service.create_user_repository(self.user, use_template=True)
    
    @patch('project.apps.git_repository.services.subprocess.run')
    @patch('project.apps.git_repository.services.tempfile.mkstemp')
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists')
    @patch('os.remove')
    @patch('os.chmod')
    def test_clone_repository(self, mock_chmod, mock_remove, mock_exists, mock_file, 
                             mock_mkstemp, mock_subprocess):
        """测试仓库克隆"""
        repo = GitRepository.objects.create(
            owner=self.user,
            repo_url='https://gitea.dhr2333.cn/beancount-trans/1-beancount.git',
            repo_name='1-beancount',
            gitea_repo_id=123,
            deploy_key_private='-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----',
            deploy_key_public='ssh-rsa test'
        )
        
        mock_mkstemp.return_value = (1, '/tmp/test_key')
        mock_exists.return_value = True
        mock_subprocess.return_value = MagicMock(returncode=0)
        
        from pathlib import Path
        target_path = Path('/tmp/test_repo')
        
        self.service._clone_repository(repo, target_path)
        
        # 验证 git clone 命令被调用
        mock_subprocess.assert_called_once()
        args, kwargs = mock_subprocess.call_args
        assert 'git' in args[0]
        assert 'clone' in args[0]
    
    @patch('project.apps.git_repository.services.tempfile.mkdtemp')
    @patch('project.apps.git_repository.services.shutil.copytree')
    def test_backup_trans_directory(self, mock_copytree, mock_mkdtemp):
        """测试 trans 目录备份"""
        mock_mkdtemp.return_value = '/tmp/backup_dir'
        
        from pathlib import Path
        trans_path = Path('/tmp/test/trans')
        
        backup_dir = self.service._backup_trans_directory(trans_path)
        
        assert backup_dir == '/tmp/backup_dir'
        mock_copytree.assert_called_once_with(trans_path, Path('/tmp/backup_dir') / 'trans')
    
    def test_rebuild_trans_main_bean_with_files(self):
        """测试重建 trans/main.bean 文件"""
        import tempfile
        import os
        from pathlib import Path
        
        with tempfile.TemporaryDirectory() as temp_dir:
            user_assets_path = Path(temp_dir)
            trans_path = user_assets_path / 'trans'
            trans_path.mkdir()
            
            # 创建一些测试文件
            (trans_path / 'file1.bean').write_text('test content 1')
            (trans_path / 'file2.bean').write_text('test content 2')
            
            self.service._rebuild_trans_main_bean(user_assets_path)
            
            main_bean_path = trans_path / 'main.bean'
            assert main_bean_path.exists()
            
            content = main_bean_path.read_text()
            assert 'include "trans/file1.bean"' in content
            assert 'include "trans/file2.bean"' in content
    
    def test_rebuild_trans_main_bean_empty(self):
        """测试重建空的 trans/main.bean 文件"""
        import tempfile
        from pathlib import Path
        
        with tempfile.TemporaryDirectory() as temp_dir:
            user_assets_path = Path(temp_dir)
            trans_path = user_assets_path / 'trans'
            trans_path.mkdir()
            
            self.service._rebuild_trans_main_bean(user_assets_path)
            
            main_bean_path = trans_path / 'main.bean'
            assert main_bean_path.exists()
            
            content = main_bean_path.read_text()
            assert 'No parsed files yet' in content
    
    @patch('project.apps.git_repository.services.zipfile.ZipFile')
    @patch('project.apps.git_repository.services.tempfile.mkdtemp')
    def test_create_trans_download_archive(self, mock_mkdtemp, mock_zipfile):
        """测试创建 trans 目录下载压缩包"""
        repo = GitRepository.objects.create(
            owner=self.user,
            repo_url='https://gitea.dhr2333.cn/beancount-trans/1-beancount.git',
            repo_name='1-beancount',
            gitea_repo_id=123,
            deploy_key_private='private_key',
            deploy_key_public='public_key'
        )
        
        mock_mkdtemp.return_value = '/tmp/test_dir'
        mock_zip_instance = MagicMock()
        mock_zipfile.return_value.__enter__.return_value = mock_zip_instance
        
        # 模拟 trans 目录存在
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.rglob', return_value=[]):
            
            zip_path = self.service.create_trans_download_archive(self.user)
        
        assert zip_path == '/tmp/test_dir/testuser_trans.zip'
    
    def test_create_trans_download_archive_no_repository(self):
        """测试没有仓库时创建下载压缩包"""
        with pytest.raises(GitServiceException, match="用户未启用 Git 功能"):
            self.service.create_trans_download_archive(self.user)

