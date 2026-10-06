from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    GitRepositoryViewSet, 
    GitSyncView, 
    GitSyncStatusView,
    GitSyncCancelView,
    GitWebhookView,
    GitTransCommitPreviewView,
    GitTransCommitView,
)

# 创建路由器并注册视图集
router = DefaultRouter()
router.register('repository', GitRepositoryViewSet, basename='git-repository')

urlpatterns = [
    # 视图集路由
    path('', include(router.urls)),

    # 同步相关
    path('sync/', GitSyncView.as_view(), name='git-sync'),
    path('sync/status/', GitSyncStatusView.as_view(), name='git-sync-status'),
    path('sync/cancel/', GitSyncCancelView.as_view(), name='git-sync-cancel'),

    # Webhook（无需认证）
    path('webhook/', GitWebhookView.as_view(), name='git-webhook'),

    # Trans 条目迁移到月度账本
    path('trans/commit/preview/', GitTransCommitPreviewView.as_view(), name='git-trans-commit-preview'),
    path('trans/commit/', GitTransCommitView.as_view(), name='git-trans-commit'),
]

