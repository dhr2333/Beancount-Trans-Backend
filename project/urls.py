"""project URL Configuration

The `urlpatterns` list routes URLs to view.py. For more information please see:
    https://docs.djangoproject.com/en/4.0/topics/http/urls/
Examples:
Function view.py
    1. Add an import:  from my_app import view.py
    2. Add a URL to urlpatterns:  path('', view.py.home, name='home')
Class-based view.py
    1. Add an import:  from other_app.view.py import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from project.apps.maps.views import ExpenseViewSet, AssetsViewSet, IncomeViewSet, TemplateViewSet,TemplateItemViewSet
from project.apps.translate.views.views import UserConfigAPI
from project.apps.file_manager.views import DirectoryViewSet, FileViewSet
from project.apps.account.views import AccountViewSet, AccountTemplateViewSet
from project.apps.tags.views import TagViewSet
from project.views import authenticateByToken
from rest_framework_simplejwt.views import TokenRefreshView
# from .views import GoogleLogin
from rest_framework import routers
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
# from rest_framework import permissions
# from drf_yasg.views import get_schema_view
# from drf_yasg import openapi
# from project.views import DRFLoginView

# from users.views import UserViewSet, GroupViewSet, CreateUserView, LoginView, GitHubLogin
# schema_view = get_schema_view(
#     openapi.Info(
#         title="文件管理API",
#         default_version='v1',
#         description="文件上传、管理和检索接口文档",
#     ),
#     public=True,
#     permission_classes=(permissions.AllowAny,),
# )

router = routers.DefaultRouter()
router.register(r'account', AccountViewSet, basename='account')
router.register(r'account-templates', AccountTemplateViewSet, basename='account-template')
router.register(r'tags', TagViewSet, basename='tag')
router.register(r'expense', ExpenseViewSet, basename="expense")
router.register(r'assets', AssetsViewSet, basename="assets")
router.register(r'income', IncomeViewSet, basename="income")
router.register(r'directories', DirectoryViewSet, basename='directory')
router.register(r'files', FileViewSet, basename='files')
router.register(r'templates', TemplateViewSet, basename='template')
router.register(
    r'templates/(?P<template_pk>\d+)/items', 
    TemplateItemViewSet, 
    basename='templateitem'
)


urlpatterns = [
    path('api/', include(router.urls)),
    path('admin/', admin.site.urls),  # 管理地址

    # API文档 - drf-spectacular
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),  # OpenAPI schema
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),  # Swagger UI
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),  # ReDoc UI

    # allauth
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path("api/_allauth/", include("allauth.headless.urls")),
    path('api/_allauth/browser/v1/auth/github/token', authenticateByToken, name='authenticateByGithubToken'),

    # 业务相关的urls
    path('api/config/', UserConfigAPI.as_view(), name='user-config'),  # 格式化输出配置
    path('api/translate/', include('project.apps.translate.urls')),  # 解析地址
    path('api/fava/', include('project.apps.fava_instances.urls')),  # fava容器服务
    path("api/accounts/", include("allauth.urls")),
    # path('api/owntracks/', include('owntracks.urls')),  # owntracks服务
]
