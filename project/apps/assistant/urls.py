from django.urls import path

from .views import AssistantChatStreamView, AssistantChatView, AssistantStatusView

urlpatterns = [
    path('chat/', AssistantChatView.as_view(), name='assistant-chat'),
    path('chat/stream/', AssistantChatStreamView.as_view(), name='assistant-chat-stream'),
    path('status/', AssistantStatusView.as_view(), name='assistant-status'),
]
