"""助手会话持久化：标题、消息顺序、LLM 上下文。"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from project.apps.assistant.models import AssistantFeedback, ChatMessage, ChatSession
from project.apps.assistant.services.assistant_service import AssistantService, StreamEvent

TITLE_MAX_LEN = 40
INTERRUPTED_REPLY = '生成已中断，请重试'
QUERY_HISTORY_HEADER = '【本轮已执行的账本查询，后续可直接引用，勿重复执行同一条 BQL】'
QUERY_PREVIEW_MAX_LEN = 1500


class SessionGeneratingError(Exception):
    """会话仍有进行中的助手生成。"""


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


def session_has_generating_message(session: ChatSession) -> bool:
    return session.messages.filter(
        role=ChatMessage.ROLE_ASSISTANT,
        generation_status=ChatMessage.STATUS_GENERATING,
    ).exists()


def ensure_session_not_generating(session: ChatSession) -> None:
    if session_has_generating_message(session):
        raise SessionGeneratingError('上一轮回复仍在生成中，请稍候或停止后再试')


def is_incomplete_assistant_message(message: ChatMessage) -> bool:
    if message.role != ChatMessage.ROLE_ASSISTANT:
        return False
    if message.generation_status == ChatMessage.STATUS_GENERATING:
        return True
    if message.generation_status in (ChatMessage.STATUS_CANCELLED, ChatMessage.STATUS_FAILED):
        return not (message.content or '').strip()
    text = (message.content or '').strip()
    return not text or text == INTERRUPTED_REPLY


def is_incomplete_assistant_content(role: str, content: str) -> bool:
    if role != ChatMessage.ROLE_ASSISTANT:
        return False
    text = (content or '').strip()
    return not text or text == INTERRUPTED_REPLY


def _truncate_preview(text: str, max_len: int = QUERY_PREVIEW_MAX_LEN) -> str:
    normalized = (text or '').strip()
    if len(normalized) <= max_len:
        return normalized
    return f'{normalized[:max_len]}…'


def format_query_history(queries: list[dict[str, Any]]) -> str:
    """将已执行 BQL 格式化为可注入 LLM 上下文的摘要块。"""
    records = [
        q for q in queries
        if q.get('bql') and q.get('result_preview')
    ]
    if not records:
        return ''
    lines = [QUERY_HISTORY_HEADER]
    for index, query in enumerate(records, start=1):
        lines.append(f'{index}. BQL: {query["bql"]}')
        lines.append(f'结果: {_truncate_preview(query["result_preview"])}')
    return '\n'.join(lines)


def _assistant_content_for_llm(message: ChatMessage) -> str:
    content = message.content or ''
    if message.role != ChatMessage.ROLE_ASSISTANT:
        return content
    history = format_query_history(message.queries or [])
    if not history:
        return content
    if content.strip():
        return f'{content}\n\n{history}'
    return history


def collect_prior_query_records(session: ChatSession) -> list[dict[str, Any]]:
    """收集会话中已完成助手回复的 BQL 记录，供数字校验与上下文引用。"""
    records: list[dict[str, Any]] = []
    for row in session.messages.order_by('position'):
        if is_incomplete_assistant_message(row):
            continue
        if row.role != ChatMessage.ROLE_ASSISTANT:
            continue
        for query in row.queries or []:
            bql = query.get('bql')
            preview = query.get('result_preview')
            if bql and preview:
                records.append({'bql': bql, 'result_preview': preview})
    return records


def build_llm_messages(session: ChatSession) -> list[dict[str, str]]:
    rows = session.messages.order_by('position')
    messages = []
    for row in rows:
        if is_incomplete_assistant_message(row):
            continue
        messages.append({
            'role': row.role,
            'content': _assistant_content_for_llm(row),
        })
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


def discard_trailing_incomplete_assistants(session: ChatSession) -> None:
    last = session.messages.order_by('-position').first()
    if last is None:
        return
    if is_incomplete_assistant_message(last):
        last.delete()


@transaction.atomic
def append_user_message(session: ChatSession, content: str) -> ChatMessage:
    ensure_session_not_generating(session)
    discard_trailing_incomplete_assistants(session)
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
def edit_user_message(session: ChatSession, message_id: UUID, content: str) -> ChatMessage:
    ensure_session_not_generating(session)
    message = session.messages.get(id=message_id, role=ChatMessage.ROLE_USER)
    session.messages.filter(position__gt=message.position).delete()
    message.content = content
    message.save(update_fields=['content', 'modified'])
    if message.position == 0 and not session.title_locked:
        session.title = truncate_session_title(content)
        session.save(update_fields=['title', 'modified'])
    else:
        ChatSession.objects.filter(pk=session.pk).update(modified=timezone.now())
    return message


@transaction.atomic
def create_placeholder_assistant_message(session: ChatSession) -> ChatMessage:
    next_position = (
        session.messages.aggregate(max_pos=Max('position'))['max_pos']
    )
    position = 0 if next_position is None else next_position + 1
    return ChatMessage.objects.create(
        session=session,
        role=ChatMessage.ROLE_ASSISTANT,
        content='',
        generation_status=ChatMessage.STATUS_GENERATING,
        position=position,
    )


@transaction.atomic
def update_assistant_message(
    message: ChatMessage,
    *,
    content: str,
    thinking: str = '',
    reasoning: str = '',
    queries: list[dict[str, Any]] | None = None,
    generation_status: str | None = None,
) -> ChatMessage:
    message.content = content
    message.thinking = thinking or ''
    message.reasoning = reasoning or ''
    message.queries = queries or []
    update_fields = ['content', 'thinking', 'reasoning', 'queries', 'modified']
    if generation_status is not None:
        message.generation_status = generation_status
        update_fields.append('generation_status')
    message.save(update_fields=update_fields)
    ChatSession.objects.filter(pk=message.session_id).update(modified=timezone.now())
    return message


@transaction.atomic
def set_message_celery_task_id(message: ChatMessage, task_id: str) -> ChatMessage:
    message.celery_task_id = task_id
    message.save(update_fields=['celery_task_id', 'modified'])
    return message


@dataclass
class StreamAccumulator:
    reply: str = ''
    thinking: str = ''
    reasoning: str = ''
    queries: list[dict[str, Any]] = field(default_factory=list)

    def apply(self, event: StreamEvent) -> None:
        if event.event == 'reasoning_delta':
            piece = event.data.get('content', '')
            self.thinking += piece
            self.reasoning += piece
        elif event.event == 'thinking_set':
            self.thinking = event.data.get('content', '') or ''
            self.reasoning = event.data.get('reasoning') or self.thinking
        elif event.event == 'delta':
            self.reply += event.data.get('content', '')
        elif event.event == 'tool_end':
            bql = event.data.get('bql')
            preview = event.data.get('result_preview')
            if bql and preview:
                record = {'bql': bql, 'result_preview': preview}
                existing = next((i for i, q in enumerate(self.queries) if q['bql'] == bql), -1)
                if existing >= 0:
                    self.queries[existing] = record
                else:
                    self.queries.append(record)
        elif event.event == 'done':
            self.reply = event.data.get('reply', self.reply)
            self.thinking = event.data.get('thinking', self.thinking) or ''
            self.reasoning = event.data.get('reasoning', self.reasoning) or ''
            self.queries = event.data.get('queries', self.queries) or []

    def persist_kwargs(self) -> dict[str, Any]:
        content = self.reply.strip() or INTERRUPTED_REPLY
        return {
            'content': content,
            'thinking': self.thinking,
            'reasoning': self.reasoning,
            'queries': self.queries,
        }


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
        generation_status=ChatMessage.STATUS_COMPLETE,
    )
    ChatSession.objects.filter(pk=session.pk).update(modified=timezone.now())
    return message


@transaction.atomic
def update_session_title(session: ChatSession, title: str) -> ChatSession:
    session.title = title.strip()[:120]
    session.title_locked = True
    session.save(update_fields=['title', 'title_locked', 'modified'])
    return session


def get_user_assistant_message(user: User, message_id: UUID) -> ChatMessage:
    return ChatMessage.objects.select_related('session').get(
        id=message_id,
        session__user=user,
        role=ChatMessage.ROLE_ASSISTANT,
    )
