from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AssistantChatStreamReconnectView,
    AssistantChatStreamView,
    AssistantChatView,
    AssistantFeedbackView,
    AssistantKeyTestView,
    AssistantMessageStopView,
    AssistantStatusView,
    ChatSessionViewSet,
)

router = DefaultRouter()
router.register(r'sessions', ChatSessionViewSet, basename='assistant-session')

urlpatterns = [
    path('chat/', AssistantChatView.as_view(), name='assistant-chat'),
    path('chat/stream/', AssistantChatStreamView.as_view(), name='assistant-chat-stream'),
    path(
        'chat/stream/<uuid:assistant_message_id>/',
        AssistantChatStreamReconnectView.as_view(),
        name='assistant-chat-stream-reconnect',
    ),
    path(
        'messages/<uuid:message_id>/stop/',
        AssistantMessageStopView.as_view(),
        name='assistant-message-stop',
    ),
    path('feedback/', AssistantFeedbackView.as_view(), name='assistant-feedback'),
    path('status/', AssistantStatusView.as_view(), name='assistant-status'),
    path('test-key/', AssistantKeyTestView.as_view(), name='assistant-test-key'),
    path('', include(router.urls)),
]
