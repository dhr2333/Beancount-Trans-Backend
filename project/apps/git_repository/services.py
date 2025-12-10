import os
import shutil
import tempfile
import logging
import subprocess
import zipfile
from pathlib import Path
from typing import Dict, Any, Optional
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from .models import GitRepository
from .clients import GiteaAPIClient, GiteaAPIException

User = get_user_model()
logger = logging.getLogger(__name__)


class GitServiceException(Exception):
    """Git 服务异常"""
    pass


class PlatformGitService:
    """平台托管 Gitea 仓库服务
    
    职责：
    - 仓库生命周期管理（创建、删除）
    - Deploy Key 管理（生成、重新生成）
    - 仓库同步（pull）
    - trans/ 目录管理
    """
    
    def __init__(self):
        self.gitea_client = GiteaAPIClient()
        self.assets_base_path = Path(settings.BASE_DIR) / 'Assets'
        
    def create_user_repository(self, user: User, use_template: bool = True) -> GitRepository:
        """为用户创建 Git 仓库
        
        Args:
            user: 用户对象
            use_template: 是否基于模板初始化
                - True: 基于 Beancount-Trans-Assets 模板创建
                - False: 创建空仓库，等待用户推送
        
        流程：
        1. 检查用户是否已有仓库
        2. 调用 Gitea API 创建仓库
        3. 生成 SSH 密钥对
        4. 添加 Deploy Key 到仓库
        5. 配置 Webhook
        6. 如果 use_template=True，初始化仓库内容
        7. 保存仓库信息到数据库
        
        Returns:
            GitRepository 实例
        """
        # 检查用户是否已有仓库
        if hasattr(user, 'git_repo'):
            raise GitServiceException("用户已有 Git 仓库")
        
        repo_name = f"{user.id}-beancount"
        
        try:
            # 1. 创建 Gitea 仓库
            logger.info(f"Creating Gitea repository for user {user.username}: {repo_name}")
            repo_data = self.gitea_client.create_repository(
                repo_name=repo_name,
                description=f"Beancount account book for {user.username}",
                private=True
            )
            
            # 2. 生成 SSH 密钥对
            private_key, public_key = self._generate_ssh_key_pair()
            
            # 3. 添加 Deploy Key
            deploy_key_data = self.gitea_client.add_deploy_key(
                repo_name=repo_name,
                title=f"Platform Deploy Key - {user.username}",
                public_key=public_key,
                read_only=False  # 需要写权限
            )
            
            # 4. 配置 Webhook (如果有配置)
            if settings.GITEA_WEBHOOK_SECRET:
                try:
                    webhook_url = f"{settings.BASE_URL}/api/git/webhook/"
                    self.gitea_client.create_webhook(
                        repo_name=repo_name,
                        webhook_url=webhook_url
                    )
                    logger.info(f"Webhook created for {repo_name}")
                except GiteaAPIException as e:
                    logger.warning(f"Failed to create webhook for {repo_name}: {e}")
                    # 不阻断流程，Webhook 可以后续手动配置
            
            # 5. 创建数据库记录
            git_repo = GitRepository.objects.create(
                owner=user,
                repo_name=repo_name,
                gitea_repo_id=repo_data['id'],
                created_with_template=use_template,
                deploy_key_id=deploy_key_data['id'],
                deploy_key_private=private_key,
                deploy_key_public=public_key,
                sync_status='pending'
            )
            
            # 6. 如果基于模板创建，初始化仓库内容
            if use_template:
                self._initialize_repository_with_template(git_repo)
            
            logger.info(f"Successfully created Git repository for user {user.username}")
            return git_repo
            
        except Exception as e:
            logger.error(f"Failed to create repository for user {user.username}: {e}")
            # 清理已创建的资源
            try:
                self.gitea_client.delete_repository(repo_name)
            except:
                pass
            raise GitServiceException(f"创建仓库失败: {e}")
    
    def sync_repository(self, user: User) -> Dict[str, Any]:
        """从远程仓库同步到本地
        
        核心处理逻辑：
        1. 备份 trans/ 目录下所有解析文件
        2. 执行 git fetch + git reset --hard origin/main（以远程为准）
        3. 恢复备份的解析文件到 trans/ 目录
        4. 重建 trans/main.bean 的 include 关系
        
        冲突处理：始终以远程仓库为准，平台本地修改会被覆盖
        
        Returns:
            同步结果信息
        """
        try:
            git_repo = user.git_repo
        except GitRepository.DoesNotExist:
            raise GitServiceException("用户未启用 Git 功能")
        
        # 更新同步状态
        git_repo.sync_status = 'syncing'
        git_repo.sync_error = ''
        git_repo.save()
        
        user_assets_path = self.assets_base_path / user.username
        
        try:
            # 1. 确保用户目录存在
            user_assets_path.mkdir(parents=True, exist_ok=True)
            
            # 2. 备份 trans/ 目录
            trans_backup = None
            trans_path = user_assets_path / 'trans'
            if trans_path.exists():
                trans_backup = self._backup_trans_directory(trans_path)
                logger.info(f"Backed up trans/ directory for user {user.username}")
            
            # 3. 检查是否为初次克隆
            git_path = user_assets_path / '.git'
            if not git_path.exists():
                # 初次克隆
                self._clone_repository(git_repo, user_assets_path)
            else:
                # 更新现有仓库
                self._pull_repository(git_repo, user_assets_path)
            
            # 4. 恢复 trans/ 目录
            if trans_backup:
                self._restore_trans_directory(trans_backup, user_assets_path / 'trans')
                logger.info(f"Restored trans/ directory for user {user.username}")
            
            # 5. 重建 trans/main.bean
            self._rebuild_trans_main_bean(user_assets_path)
            
            # 6. 更新同步状态
            git_repo.sync_status = 'success'
            git_repo.last_sync_at = timezone.now()
            git_repo.save()
            
            logger.info(f"Successfully synced repository for user {user.username}")
            
            return {
                'status': 'success',
                'message': '同步成功',
                'synced_at': git_repo.last_sync_at
            }
            
        except Exception as e:
            # 记录错误并更新状态
            error_msg = str(e)
            logger.error(f"Failed to sync repository for user {user.username}: {error_msg}")
            
            git_repo.sync_status = 'failed'
            git_repo.sync_error = error_msg
            git_repo.save()
            
            return {
                'status': 'failed',
                'message': f'同步失败: {error_msg}',
                'error': error_msg
            }
    
    def regenerate_deploy_key(self, user: User) -> Dict[str, str]:
        """重新生成 Deploy Key
        
        流程：
        1. 生成新的 SSH 密钥对
        2. 删除 Gitea 上的旧 Deploy Key
        3. 添加新的 Deploy Key
        4. 更新数据库记录
        
        Returns:
            包含新密钥信息的字典
        """
        try:
            git_repo = user.git_repo
        except GitRepository.DoesNotExist:
            raise GitServiceException("用户未启用 Git 功能")
        
        try:
            # 1. 生成新的密钥对
            private_key, public_key = self._generate_ssh_key_pair()
            
            # 2. 删除旧的 Deploy Key（如果存在）
            if git_repo.deploy_key_id:
                try:
                    self.gitea_client.delete_deploy_key(git_repo.repo_name, git_repo.deploy_key_id)
                except GiteaAPIException as e:
                    logger.warning(f"Failed to delete old deploy key: {e}")
            
            # 3. 添加新的 Deploy Key
            deploy_key_data = self.gitea_client.add_deploy_key(
                repo_name=git_repo.repo_name,
                title=f"Platform Deploy Key - {user.username} (Regenerated)",
                public_key=public_key,
                read_only=False
            )
            
            # 4. 更新数据库记录
            git_repo.deploy_key_id = deploy_key_data['id']
            git_repo.deploy_key_private = private_key
            git_repo.deploy_key_public = public_key
            git_repo.save()
            
            logger.info(f"Successfully regenerated deploy key for user {user.username}")
            
            return {
                'private_key': private_key,
                'public_key': public_key,
                'key_id': deploy_key_data['id']
            }
            
        except Exception as e:
            logger.error(f"Failed to regenerate deploy key for user {user.username}: {e}")
            raise GitServiceException(f"重新生成 Deploy Key 失败: {e}")
    
    def create_trans_download_archive(self, user: User) -> str:
        """创建 trans/ 目录的 ZIP 压缩包供用户下载
        
        Returns:
            ZIP 文件的路径
        """
        try:
            git_repo = user.git_repo
        except GitRepository.DoesNotExist:
            raise GitServiceException("用户未启用 Git 功能")
        
        user_assets_path = self.assets_base_path / user.username
        trans_path = user_assets_path / 'trans'
        
        if not trans_path.exists():
            raise GitServiceException("trans/ 目录不存在")
        
        # 创建临时 ZIP 文件
        temp_dir = tempfile.mkdtemp()
        zip_path = os.path.join(temp_dir, f"{user.username}_trans.zip")
        
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in trans_path.rglob('*.bean'):
                    arcname = str(file_path.relative_to(trans_path))
                    zipf.write(file_path, arcname)
            
            logger.info(f"Created trans/ archive for user {user.username}: {zip_path}")
            return zip_path
            
        except Exception as e:
            # 清理临时文件
            if os.path.exists(zip_path):
                os.remove(zip_path)
            raise GitServiceException(f"创建压缩包失败: {e}")
    
    def _generate_ssh_key_pair(self) -> tuple[str, str]:
        """生成 SSH 密钥对
        
        Returns:
            (private_key_pem, public_key_openssh) 元组
        """
        # 生成 RSA 密钥对
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=4096
        )
        
        # 序列化私钥为 PEM 格式
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode('utf-8')
        
        # 序列化公钥为 OpenSSH 格式
        public_key = private_key.public_key()
        public_openssh = public_key.public_bytes(
            encoding=serialization.Encoding.OpenSSH,
            format=serialization.PublicFormat.OpenSSH
        ).decode('utf-8')
        
        return private_pem, public_openssh
    
    def _initialize_repository_with_template(self, git_repo: GitRepository):
        """使用 Beancount-Trans-Assets 模板初始化仓库"""
        # TODO: 实现模板初始化逻辑
        # 这里需要将 Beancount-Trans-Assets 的内容推送到新创建的仓库
        logger.info(f"Template initialization for {git_repo.repo_name} - TODO: implement")
        pass
    
    def _clone_repository(self, git_repo: GitRepository, target_path: Path):
        """克隆仓库到本地"""
        # 准备 SSH 密钥
        ssh_key_file = self._prepare_ssh_key(git_repo)
        
        try:
            # 使用 SSH 克隆
            clone_url = git_repo.ssh_clone_url
            
            # 设置 GIT_SSH_COMMAND 环境变量
            env = os.environ.copy()
            env['GIT_SSH_COMMAND'] = f'ssh -i {ssh_key_file} -o StrictHostKeyChecking=no'
            
            result = subprocess.run([
                'git', 'clone', clone_url, str(target_path)
            ], env=env, capture_output=True, text=True, check=True)
            
            logger.info(f"Cloned repository {git_repo.repo_name} to {target_path}")
            
        finally:
            # 清理临时 SSH 密钥文件
            if os.path.exists(ssh_key_file):
                os.remove(ssh_key_file)
    
    def _pull_repository(self, git_repo: GitRepository, repo_path: Path):
        """更新现有仓库"""
        ssh_key_file = self._prepare_ssh_key(git_repo)
        
        try:
            # 设置环境变量
            env = os.environ.copy()
            env['GIT_SSH_COMMAND'] = f'ssh -i {ssh_key_file} -o StrictHostKeyChecking=no'
            
            # 切换到仓库目录
            original_cwd = os.getcwd()
            os.chdir(repo_path)
            
            try:
                # fetch 最新内容
                subprocess.run(['git', 'fetch', 'origin'], env=env, check=True)
                
                # 强制重置到远程分支
                subprocess.run(['git', 'reset', '--hard', 'origin/main'], check=True)
                
                logger.info(f"Updated repository {git_repo.repo_name}")
                
            finally:
                os.chdir(original_cwd)
                
        finally:
            if os.path.exists(ssh_key_file):
                os.remove(ssh_key_file)
    
    def _prepare_ssh_key(self, git_repo: GitRepository) -> str:
        """准备临时 SSH 密钥文件"""
        # 创建临时文件
        fd, ssh_key_file = tempfile.mkstemp(suffix='.pem')
        
        try:
            # 写入私钥内容
            with os.fdopen(fd, 'w') as f:
                f.write(git_repo.deploy_key_private)
            
            # 设置文件权限
            os.chmod(ssh_key_file, 0o600)
            
            return ssh_key_file
            
        except:
            os.close(fd)
            if os.path.exists(ssh_key_file):
                os.remove(ssh_key_file)
            raise
    
    def _backup_trans_directory(self, trans_path: Path) -> str:
        """备份 trans/ 目录"""
        backup_dir = tempfile.mkdtemp(prefix='trans_backup_')
        shutil.copytree(trans_path, Path(backup_dir) / 'trans')
        return backup_dir
    
    def _restore_trans_directory(self, backup_dir: str, trans_path: Path):
        """恢复 trans/ 目录"""
        if trans_path.exists():
            shutil.rmtree(trans_path)
        
        backup_trans = Path(backup_dir) / 'trans'
        if backup_trans.exists():
            shutil.copytree(backup_trans, trans_path)
        
        # 清理备份
        shutil.rmtree(backup_dir)
    
    def _rebuild_trans_main_bean(self, user_assets_path: Path):
        """重建 trans/main.bean 的 include 关系"""
        trans_path = user_assets_path / 'trans'
        trans_main_file = trans_path / 'main.bean'
        
        if not trans_path.exists():
            return
        
        # 收集所有 .bean 文件（除了 main.bean）
        bean_files = []
        for bean_file in trans_path.glob('*.bean'):
            if bean_file.name != 'main.bean':
                bean_files.append(bean_file.name)
        
        # 生成 include 语句
        if bean_files:
            bean_files.sort()  # 按字母顺序排序
            
            content = "; Trans directory - Auto-generated includes\n"
            content += "; This file is automatically generated by the platform\n\n"
            
            for bean_file in bean_files:
                content += f'include "trans/{bean_file}"\n'
            
            # 写入文件
            trans_main_file.write_text(content, encoding='utf-8')
            logger.info(f"Rebuilt trans/main.bean with {len(bean_files)} includes")
        else:
            # 如果没有文件，创建空的 main.bean
            if not trans_main_file.exists():
                trans_main_file.write_text(
                    "; Trans directory - No parsed files yet\n",
                    encoding='utf-8'
                )
