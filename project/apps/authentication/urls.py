from django.urls import path, include
from rest_framework.routers import DefaultRouter
from project.apps.authentication.views import (
    PhoneAuthViewSet,
    EmailAuthViewSet,
    AccountBindingViewSet,
    UserProfileViewSet,
    TwoFactorAuthViewSet,
)

router = DefaultRouter()
router.register(r'phone', PhoneAuthViewSet, basename='phone-auth')
router.register(r'email', EmailAuthViewSet, basename='email-auth')
router.register(r'bindings', AccountBindingViewSet, basename='account-binding')
router.register(r'profile', UserProfileViewSet, basename='user-profile')
router.register(r'2fa', TwoFactorAuthViewSet, basename='2fa')

urlpatterns = [
    path('', include(router.urls)),
]

