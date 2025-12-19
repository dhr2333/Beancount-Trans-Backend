import os
import hashlib
import hmac
import logging
from django.conf import settings
from django.http import Http404, HttpResponse, FileResponse
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet
from drf_spectacular.utils import extend_schema, OpenApiResponse

from .models import GitRepository
from .serializers import (
    GitRepositorySerializer, CreateRepositorySerializer,
    SyncStatusSerializer, SyncResponseSerializer,
    WebhookPayloadSerializer, DeployKeyResponseSerializer,
    DeleteRepositoryResponseSerializer
)
from .services import PlatformGitService, GitServiceException

logger = logging.getLogger(__name__)


class GitRepositoryViewSet(ViewSet):
    """Git 仓库管理视图集"""

    permission_classes = [permissions.IsAuthenticated]

    def get_git_service(self):
        """获取 Git 服务实例"""
        return PlatformGitService()

    @extend_schema(
        summary="获取用户 Git 仓库信息",
        responses={
            200: GitRepositorySerializer,
            404: OpenApiResponse(description="用户未启用 Git 功能")
        }
    )
    def list(self, request: Request) -> Response:
        """获取用户的 Git 仓库信息"""
        try:
            git_repo = request.user.git_repo
            serializer = GitRepositorySerializer(git_repo)
            return Response(serializer.data)
        except GitRepository.DoesNotExist:
            return Response(
                {'error': '用户未启用 Git 功能'}, 
                status=status.HTTP_404_NOT_FOUND
            )

    @extend_schema(
        summary="启用 Git 功能",
        request=CreateRepositorySerializer,
        responses={
            201: GitRepositorySerializer,
            400: OpenApiResponse(description="请求参数错误或用户已有仓库")
        }
    )
    def create(self, request: Request) -> Response:
        """启用 Git 功能，创建用户仓库"""
        serializer = CreateRepositorySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        use_template = serializer.validated_data['template']

        try:
            git_service = self.get_git_service()
            git_repo = git_service.create_user_repository(
                user=request.user, 
                use_template=use_template
            )

            response_serializer = GitRepositorySerializer(git_repo)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        except GitServiceException as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )

    @extend_schema(
        summary="下载 Deploy Key",
        responses={
            200: DeployKeyResponseSerializer,
            404: OpenApiResponse(description="用户未启用 Git 功能")
        }
    )
    @action(detail=False, methods=['GET'], url_path='deploy-key')
    def download_deploy_key(self, request: Request) -> Response:
        """下载 Deploy Key 私钥文件"""
        try:
            git_repo = request.user.git_repo

            # 创建文件响应
            filename = f"{request.user.username}_deploy_key.pem"

            response = HttpResponse(
                git_repo.deploy_key_private,
                content_type='application/x-pem-file'
            )
            response['Content-Disposition'] = f'attachment; filename="{filename}"'

            return response

        except GitRepository.DoesNotExist:
            return Response(
                {'error': '用户未启用 Git 功能'}, 
                status=status.HTTP_404_NOT_FOUND
            )

    @extend_schema(
        summary="重新生成 Deploy Key",
        responses={
            200: DeployKeyResponseSerializer,
            404: OpenApiResponse(description="用户未启用 Git 功能"),
            500: OpenApiResponse(description="重新生成失败")
        }
    )
    @action(detail=False, methods=['POST'], url_path='deploy-key/regenerate')
    def regenerate_deploy_key(self, request: Request) -> Response:
        """重新生成 Deploy Key 并下载"""
        try:
            git_service = self.get_git_service()
            key_data = git_service.regenerate_deploy_key(request.user)

            # 创建文件响应
            filename = f"{request.user.username}_deploy_key.pem"

            response = HttpResponse(
                key_data['private_key'],
                content_type='application/x-pem-file'
            )
            response['Content-Disposition'] = f'attachment; filename="{filename}"'

            return response

        except GitRepository.DoesNotExist:
            return Response(
                {'error': '用户未启用 Git 功能'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except GitServiceException as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(
        summary="删除用户 Git 仓库",
        responses={
            200: DeleteRepositoryResponseSerializer,
            404: OpenApiResponse(description="用户未启用 Git 功能"),
            500: OpenApiResponse(description="删除失败")
        }
    )
    @action(detail=False, methods=['DELETE'], url_path='delete')
    def delete_repository(self, request: Request) -> Response:
        """删除用户 Git 仓库并清理相关资源"""
        try:
            git_repo = request.user.git_repo

            git_service = self.get_git_service()
            result = git_service.delete_user_repository(request.user)

            serializer = DeleteRepositoryResponseSerializer(result)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except GitRepository.DoesNotExist:
            return Response(
                {'error': '用户未启用 Git 功能'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except GitServiceException as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GitSyncView(APIView):
    """Git 同步视图"""

    permission_classes = [permissions.IsAuthenticated]

    def get_git_service(self):
        return PlatformGitService()

    @extend_schema(
        summary="手动触发同步",
        responses={
            200: SyncResponseSerializer,
            404: OpenApiResponse(description="用户未启用 Git 功能")
        }
    )
    def post(self, request: Request) -> Response:
        """手动触发从远程仓库同步"""
        try:
            git_service = self.get_git_service()
            result = git_service.sync_repository(request.user)

            serializer = SyncResponseSerializer(result)
            return Response(serializer.data)

        except GitServiceException as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_404_NOT_FOUND
            )


class GitSyncStatusView(APIView):
    """Git 同步状态视图"""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="获取同步状态",
        responses={
            200: SyncStatusSerializer,
            404: OpenApiResponse(description="用户未启用 Git 功能")
        }
    )
    def get(self, request: Request) -> Response:
        """获取同步状态和错误信息"""
        try:
            git_repo = request.user.git_repo

            data = {
                'status': git_repo.sync_status,
                'last_sync_at': git_repo.last_sync_at,
                'error': git_repo.sync_error
            }

            serializer = SyncStatusSerializer(data)
            return Response(serializer.data)

        except GitRepository.DoesNotExist:
            return Response(
                {'error': '用户未启用 Git 功能'}, 
                status=status.HTTP_404_NOT_FOUND
            )


class GitWebhookView(APIView):
    """Git Webhook 视图"""

    permission_classes = []  # 无需认证，通过签名验证

    def get_git_service(self):
        return PlatformGitService()

    @extend_schema(
        summary="处理 Gitea Webhook",
        request=WebhookPayloadSerializer,
        responses={
            200: OpenApiResponse(description="处理成功"),
            400: OpenApiResponse(description="签名验证失败"),
            404: OpenApiResponse(description="仓库不存在")
        }
    )
    def post(self, request: Request) -> Response:
        """处理 Gitea push 事件 Webhook"""
        # 验证 Webhook 签名
        if not self._verify_webhook_signature(request):
            return Response(
                {'error': 'Invalid signature'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # 解析 payload
        try:
            serializer = WebhookPayloadSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            payload = serializer.validated_data
            repo_name = payload['repository']['name']

            # 从仓库名查找对应的 Git 仓库
            # 仓库名格式：{uuid}-assets
            if not repo_name.endswith('-assets'):
                return Response({'error': 'Invalid repository name format'})

            # 直接通过仓库名查找，不依赖用户ID解析
            try:
                git_repo = GitRepository.objects.get(repo_name=repo_name)
            except GitRepository.DoesNotExist:
                return Response(
                    {'error': 'Repository not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )

            # 触发同步
            git_service = self.get_git_service()
            result = git_service.sync_repository(git_repo.owner)

            logger.info(f"Webhook triggered sync for {repo_name}: {result['status']}")

            return Response({
                'message': 'Sync triggered successfully',
                'status': result['status']
            })

        except Exception as e:
            logger.error(f"Webhook processing error: {e}")
            return Response(
                {'error': 'Processing failed'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _verify_webhook_signature(self, request: Request) -> bool:
        """验证 Webhook 签名"""
        if not settings.GITEA_WEBHOOK_SECRET:
            return True  # 如果没有配置密钥，跳过验证

        signature = request.headers.get('X-Gitea-Signature')
        if not signature:
            return False

        # 计算期望的签名
        body = request.body
        expected_signature = hmac.new(
            settings.GITEA_WEBHOOK_SECRET.encode(),
            body,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(signature, expected_signature)


class GitTransDownloadView(APIView):
    """Git Trans 目录下载视图"""

    permission_classes = [permissions.IsAuthenticated]

    def get_git_service(self):
        return PlatformGitService()

    @extend_schema(
        summary="下载 trans 目录",
        responses={
            200: OpenApiResponse(description="ZIP 文件"),
            404: OpenApiResponse(description="用户未启用 Git 功能或 trans 目录不存在")
        }
    )
    def get(self, request: Request) -> Response:
        """下载 trans/ 目录的 ZIP 压缩包"""
        try:
            git_service = self.get_git_service()
            zip_path = git_service.create_trans_download_archive(request.user)

            # 创建文件响应
            filename = f"{request.user.username}_trans.zip"

            response = FileResponse(
                open(zip_path, 'rb'),
                content_type='application/zip'
            )
            response['Content-Disposition'] = f'attachment; filename="{filename}"'

            # 清理临时文件（在响应发送后）
            def cleanup():
                try:
                    os.remove(zip_path)
                except:
                    pass

            # 注册清理函数（Django 会在响应发送后调用）
            response._cleanup_func = cleanup

            return response

        except GitServiceException as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_404_NOT_FOUND
            )