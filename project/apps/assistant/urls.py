from django.urls import path

from .views import (
    AssistantChatStreamView,
    AssistantChatView,
    AssistantFeedbackView,
    AssistantStatusView,
)

urlpatterns = [
    path('chat/', AssistantChatView.as_view(), name='assistant-chat'),
    path('chat/stream/', AssistantChatStreamView.as_view(), name='assistant-chat-stream'),
    path('feedback/', AssistantFeedbackView.as_view(), name='assistant-feedback'),
    path('status/', AssistantStatusView.as_view(), name='assistant-status'),
]
