from django.urls import path, include
from rest_framework import routers
from . import views
from .views import UserViewSet, GroupViewSet

router = routers.DefaultRouter()
router.register(r'users', UserViewSet, basename="user")
router.register(r'groups', GroupViewSet, basename="group")


urlpatterns = [
    path('', include(router.urls)),
    path('create', views.CreateUserView.as_view()),
]
