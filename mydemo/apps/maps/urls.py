from django.urls import include, path
from rest_framework import routers
from .views import ExpenseViewSet, AssetsViewSet

router = routers.DefaultRouter()
router.register(r'expense', ExpenseViewSet, basename="expense")
router.register(r'assets', AssetsViewSet, basename="assets")


urlpatterns = [
    path('', include(router.urls)),
]
