"""
对账模块 URL 配置
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import ScheduledTaskViewSet, RecurringTaskViewSet

router = DefaultRouter()
router.register('tasks', ScheduledTaskViewSet, basename='scheduled-task')
router.register('recurring-tasks', RecurringTaskViewSet, basename='recurring-task')

urlpatterns = [
    path('', include(router.urls)),
]



