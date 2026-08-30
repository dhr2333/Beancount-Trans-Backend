from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AssistantChatStreamView,
    AssistantChatView,
    AssistantFeedbackView,
    AssistantStatusView,
    ChatSessionViewSet,
)

router = DefaultRouter()
router.register(r'sessions', ChatSessionViewSet, basename='assistant-session')

urlpatterns = [
    path('chat/', AssistantChatView.as_view(), name='assistant-chat'),
    path('chat/stream/', AssistantChatStreamView.as_view(), name='assistant-chat-stream'),
    path('feedback/', AssistantFeedbackView.as_view(), name='assistant-feedback'),
    path('status/', AssistantStatusView.as_view(), name='assistant-status'),
    path('', include(router.urls)),
]
