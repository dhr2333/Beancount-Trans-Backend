"""mydemo URL Configuration

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
from account.views import AccountViewSet
from django.contrib import admin
from django.urls import path, include
from maps.views import ExpenseViewSet, AssetsViewSet, IncomeViewSet
from rest_framework import routers
from rest_framework.documentation import include_docs_urls
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView
from users.views import UserViewSet, GroupViewSet, CreateUserView, LoginView

router = routers.DefaultRouter()
router.register(r'expense', ExpenseViewSet, basename="expense")
router.register(r'aassets', AssetsViewSet, basename="assets")
router.register(r'income', IncomeViewSet, basename="income")
router.register(r'account', AccountViewSet, basename="account")
router.register(r'users', UserViewSet, basename="user")
router.register(r'groups', GroupViewSet, basename="group")

urlpatterns = [
    path('', include(router.urls)),

    path('admin/', admin.site.urls),
    path('docs/', include_docs_urls(title='Beancount-Trans')),
    path('accounts/', include('rest_framework.urls', namespace='rest_framework')),  # DRF 提供的一系列身份认证的接口，用于在页面中认证身份

    path('translate/', include('translate.urls')),
    path('api/owntracks/', include('owntracks.urls')),

    path('user/create/', CreateUserView.as_view(), name='create_user'),  # 创建用户
    path('login/', LoginView.as_view(), name='user_login'),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),  # 获取Token
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),  # 刷新Token有效期
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),  # 验证Token的有效性

    # path('api/get_csrf_token/', get_csrf_token, name='token_verify')
    # path('users/', include('users.urls')),
    # path('maps/', include('maps.urls')),
]
