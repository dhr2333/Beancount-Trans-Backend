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
# from account.views import AccountViewSet
from django.contrib import admin
from django.urls import path, include
from maps.views import ExpenseViewSet, AssetsViewSet, IncomeViewSet
from translate.views.views import UserConfigAPI
from file_manager.views import DirectoryViewSet, FileViewSet
# from .views import GoogleLogin
from rest_framework import routers
from rest_framework.documentation import include_docs_urls
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView
from .views import authenticateByToken
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
router.register(r'expense', ExpenseViewSet, basename="expense")
router.register(r'aassets', AssetsViewSet, basename="assets")
router.register(r'income', IncomeViewSet, basename="income")
# router.register(r'account', AccountViewSet, basename="account")
router.register(r'directories', DirectoryViewSet, basename='directory')
router.register(r'files', FileViewSet, basename='files')


urlpatterns = [
    path('api/', include(router.urls)),
    path('admin/', admin.site.urls),  # 管理地址
    path('docs/', include_docs_urls(title='Beancount-Trans')),  # API文档
    # path('swagger/', schema_view.with_ui('swagger', cache_timeout=0)),
    # path('redoc/', schema_view.with_ui('redoc', cache_timeout=0)),

    # 用户权限相关的urls
    path('api/config/', UserConfigAPI.as_view(), name='user-config'),  # 登录认证
    path('api/auth/', include('dj_rest_auth.urls')),  # 登录认证
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),  # 获取Token
    path('api/token/verify/', TokenVerifyView.as_view(), name='token_verify'),  # 验证Token的有效性
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),  # 刷新Token有效期

    # allauth
    path("api/accounts/", include("allauth.urls")),
    path("api/_allauth/", include("allauth.headless.urls")),
    path('api/_allauth/browser/v1/auth/github/token', authenticateByToken, name='authenticateByGithubToken'),

    # 业务相关的urls
    path('api/translate/', include('translate.urls')),  # 解析地址
    path('api/fava/', include('fava_instances.urls')),  # fava容器服务
    # path('api/owntracks/', include('owntracks.urls')),  # owntracks服务
]
