import logging
import requests
from django.conf import settings
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class GiteaAPIException(Exception):
    """Gitea API 异常"""
    def __init__(self, message: str, status_code: int = None, response_data: dict = None):
        self.message = message
        self.status_code = status_code
        self.response_data = response_data
        super().__init__(message)


class GiteaAPIClient:
    """Gitea API 客户端

    封装所有 Gitea API 调用，使用平台管理员 Token 进行认证
    """

    def __init__(self):
        self.base_url = settings.GITEA_BASE_URL
        self.token = settings.GITEA_ADMIN_TOKEN
        self.org_name = settings.GITEA_ORG_NAME

        if not self.token:
            raise ValueError("GITEA_ADMIN_TOKEN environment variable is required")

        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'token {self.token}',
            'Content-Type': 'application/json'
        })

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """发起API请求并处理响应"""
        url = f"{self.base_url}/api/v1{endpoint}"

        try:
            response = self.session.request(method, url, **kwargs)

            # 记录请求日志
            logger.info(f"Gitea API: {method} {endpoint} -> {response.status_code}")

            # 检查响应状态
            if response.status_code >= 400:
                error_msg = f"Gitea API error: {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg += f" - {error_data.get('message', 'Unknown error')}"
                except:
                    error_msg += f" - {response.text}"

                raise GiteaAPIException(
                    message=error_msg,
                    status_code=response.status_code,
                    response_data=error_data if 'error_data' in locals() else None
                )

            return response.json() if response.content else {}

        except requests.RequestException as e:
            logger.error(f"Gitea API request failed: {e}")
            raise GiteaAPIException(f"Network error: {e}")

    def create_repository(self, repo_name: str, description: str = "", private: bool = True) -> Dict[str, Any]:
        """在 beancount-trans 组织下创建仓库

        Args:
            repo_name: 仓库名称
            description: 仓库描述
            private: 是否私有仓库

        Returns:
            仓库信息字典，包含 id, clone_url, ssh_url 等
        """
        data = {
            "name": repo_name,
            "description": description,
            "private": private,
            "auto_init": False,  # 不自动初始化
            "default_branch": "main",
            "has_issues": False,
            "has_wiki": False,
            "has_pull_requests": False,
            "has_projects": False,
            "archived": False
        }

        logger.info(f"Creating repository: {self.org_name}/{repo_name}")
        return self._make_request('POST', f'/orgs/{self.org_name}/repos', json=data)

    def delete_repository(self, repo_name: str) -> None:
        """删除仓库

        Args:
            repo_name: 仓库名称
        """
        logger.info(f"Deleting repository: {self.org_name}/{repo_name}")
        self._make_request('DELETE', f'/repos/{self.org_name}/{repo_name}')

    def add_deploy_key(self, repo_name: str, title: str, public_key: str, read_only: bool = False) -> Dict[str, Any]:
        """添加 Deploy Key

        Args:
            repo_name: 仓库名称
            title: Deploy Key 标题
            public_key: SSH 公钥内容
            read_only: 是否只读

        Returns:
            Deploy Key 信息，包含 id, title, key 等
        """
        data = {
            "title": title,
            "key": public_key,
            "read_only": read_only
        }

        logger.info(f"Adding deploy key to {self.org_name}/{repo_name}: {title}")
        return self._make_request('POST', f'/repos/{self.org_name}/{repo_name}/keys', json=data)

    def delete_deploy_key(self, repo_name: str, key_id: int) -> None:
        """删除 Deploy Key

        Args:
            repo_name: 仓库名称
            key_id: Deploy Key ID
        """
        logger.info(f"Deleting deploy key {key_id} from {self.org_name}/{repo_name}")
        self._make_request('DELETE', f'/repos/{self.org_name}/{repo_name}/keys/{key_id}')

    def create_webhook(self, repo_name: str, webhook_url: str, secret: str = None) -> Dict[str, Any]:
        """创建 Webhook

        Args:
            repo_name: 仓库名称
            webhook_url: Webhook 回调URL
            secret: Webhook 签名密钥

        Returns:
            Webhook 信息
        """
        data = {
            "type": "gitea",
            "config": {
                "url": webhook_url,
                "content_type": "json",
                "secret": secret or settings.GITEA_WEBHOOK_SECRET
            },
            "events": ["push"],  # 只监听 push 事件
            "active": True
        }

        logger.info(f"Creating webhook for {self.org_name}/{repo_name}: {webhook_url}")
        return self._make_request('POST', f'/repos/{self.org_name}/{repo_name}/hooks', json=data)

    def get_repository_info(self, repo_name: str) -> Dict[str, Any]:
        """获取仓库信息

        Args:
            repo_name: 仓库名称

        Returns:
            仓库详细信息
        """
        return self._make_request('GET', f'/repos/{self.org_name}/{repo_name}')

    def get_repository_size(self, repo_name: str) -> int:
        """获取仓库大小（字节）

        Args:
            repo_name: 仓库名称

        Returns:
            仓库大小（字节）
        """
        repo_info = self.get_repository_info(repo_name)
        return repo_info.get('size', 0) * 1024  # Gitea返回的是KB，转换为字节

    def list_deploy_keys(self, repo_name: str) -> list:
        """获取仓库的所有 Deploy Key

        Args:
            repo_name: 仓库名称

        Returns:
            Deploy Key 列表
        """
        return self._make_request('GET', f'/repos/{self.org_name}/{repo_name}/keys')

    def check_repository_exists(self, repo_name: str) -> bool:
        """检查仓库是否存在

        Args:
            repo_name: 仓库名称

        Returns:
            仓库是否存在
        """
        try:
            self.get_repository_info(repo_name)
            return True
        except GiteaAPIException as e:
            if e.status_code == 404:
                return False
            raise

