from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    GitRepositoryViewSet, 
    GitSyncView, 
    GitSyncStatusView,
    GitWebhookView,
    GitTransDownloadView
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

    # Webhook（无需认证）
    path('webhook/', GitWebhookView.as_view(), name='git-webhook'),

    # Trans 目录下载
    path('trans/download/', GitTransDownloadView.as_view(), name='git-trans-download'),
]

