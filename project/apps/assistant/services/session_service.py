"""助手会话持久化：标题、消息顺序、LLM 上下文。"""
from __future__ import annotations

import re
from typing import Any
from uuid import UUID

from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from project.apps.assistant.models import AssistantFeedback, ChatMessage, ChatSession
from project.apps.assistant.services.assistant_service import AssistantService

TITLE_MAX_LEN = 40


def truncate_session_title(text: str, max_len: int = TITLE_MAX_LEN) -> str:
    normalized = re.sub(r'\s+', ' ', (text or '').strip())
    if not normalized:
        return '新对话'
    if len(normalized) <= max_len:
        return normalized
    return f'{normalized[:max_len]}…'


def get_user_session(user: User, session_id: UUID) -> ChatSession:
    return ChatSession.objects.get(id=session_id, user=user)


def list_user_sessions(user: User, *, search: str = '', limit: int = 50) -> list[ChatSession]:
    qs = ChatSession.objects.filter(user=user).order_by('-modified')
    if search.strip():
        qs = qs.filter(title__icontains=search.strip())
    return list(qs[:limit])


def build_llm_messages(session: ChatSession) -> list[dict[str, str]]:
    rows = session.messages.order_by('position').values('role', 'content')
    messages = [{'role': row['role'], 'content': row['content']} for row in rows]
    if len(messages) > AssistantService.MAX_MESSAGES:
        messages = messages[-AssistantService.MAX_MESSAGES:]
    return messages


def feedback_map_for_messages(user: User, message_ids: list[UUID]) -> dict[str, str]:
    if not message_ids:
        return {}
    rows = AssistantFeedback.objects.filter(
        user=user,
        message_id__in=message_ids,
    ).values('message_id', 'rating')
    return {str(row['message_id']): row['rating'] for row in rows}


@transaction.atomic
def create_session_with_user_message(user: User, content: str) -> tuple[ChatSession, ChatMessage]:
    title = truncate_session_title(content)
    session = ChatSession.objects.create(user=user, title=title)
    message = ChatMessage.objects.create(
        session=session,
        role=ChatMessage.ROLE_USER,
        content=content,
        position=0,
    )
    return session, message


@transaction.atomic
def append_user_message(session: ChatSession, content: str) -> ChatMessage:
    next_position = (
        session.messages.aggregate(max_pos=Max('position'))['max_pos']
    )
    position = 0 if next_position is None else next_position + 1
    return ChatMessage.objects.create(
        session=session,
        role=ChatMessage.ROLE_USER,
        content=content,
        position=position,
    )


@transaction.atomic
def save_assistant_message(
    session: ChatSession,
    *,
    content: str,
    thinking: str = '',
    reasoning: str = '',
    queries: list[dict[str, Any]] | None = None,
) -> ChatMessage:
    next_position = (
        session.messages.aggregate(max_pos=Max('position'))['max_pos']
    )
    position = 0 if next_position is None else next_position + 1
    message = ChatMessage.objects.create(
        session=session,
        role=ChatMessage.ROLE_ASSISTANT,
        content=content,
        thinking=thinking or '',
        reasoning=reasoning or '',
        queries=queries or [],
        position=position,
    )
    ChatSession.objects.filter(pk=session.pk).update(modified=timezone.now())
    return message


@transaction.atomic
def update_session_title(session: ChatSession, title: str) -> ChatSession:
    session.title = title.strip()[:120]
    session.title_locked = True
    session.save(update_fields=['title', 'title_locked', 'modified'])
    return session
