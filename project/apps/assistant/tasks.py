"""助手 Celery 后台生成任务。"""
from __future__ import annotations

import logging
import time
from typing import Any
from uuid import UUID

from celery import shared_task
from django.contrib.auth import get_user_model

from project.apps.assistant.models import ChatMessage, ChatSession
from project.apps.assistant.services.assistant_service import AssistantService
from project.apps.assistant.services.event_bus import is_cancelled, publish, reset_stream
from project.apps.assistant.services.ledger_query import LedgerNotFoundError
from project.apps.assistant.services.session_service import (
    StreamAccumulator,
    build_llm_messages,
    update_assistant_message,
)

logger = logging.getLogger(__name__)

PERSIST_INTERVAL_SECONDS = 0.5


def _message_is_terminal(message: ChatMessage) -> bool:
    return message.generation_status != ChatMessage.STATUS_GENERATING


def _persist_from_accumulator(
    message: ChatMessage,
    accumulator: StreamAccumulator,
    *,
    generation_status: str,
) -> ChatMessage:
    kwargs = accumulator.persist_kwargs()
    return update_assistant_message(
        message,
        content=kwargs['content'],
        thinking=kwargs['thinking'],
        reasoning=kwargs['reasoning'],
        queries=kwargs['queries'],
        generation_status=generation_status,
    )


def _finalize_done(
    message: ChatMessage,
    session: ChatSession,
    user_message: ChatMessage,
    accumulator: StreamAccumulator,
    done_data: dict[str, Any],
) -> None:
    saved = update_assistant_message(
        message,
        content=done_data['reply'],
        thinking=done_data.get('thinking', ''),
        reasoning=done_data.get('reasoning', ''),
        queries=done_data.get('queries', []),
        generation_status=ChatMessage.STATUS_COMPLETE,
    )
    payload = {
        **done_data,
        'session_id': str(session.id),
        'user_message_id': str(user_message.id),
        'assistant_message_id': str(saved.id),
    }
    publish(message.id, 'done', payload)


def _finalize_error(message: ChatMessage, detail: str) -> None:
    update_assistant_message(
        message,
        content=detail,
        generation_status=ChatMessage.STATUS_FAILED,
    )
    publish(message.id, 'error', {'detail': detail})


def _finalize_cancelled(message: ChatMessage, accumulator: StreamAccumulator) -> None:
    kwargs = accumulator.persist_kwargs()
    content = kwargs['content']
    if content == '生成已中断，请重试':
        content = '已停止生成'
    _persist_from_accumulator(
        message,
        StreamAccumulator(
            reply=content,
            thinking=kwargs['thinking'],
            reasoning=kwargs['reasoning'],
            queries=kwargs['queries'],
        ),
        generation_status=ChatMessage.STATUS_CANCELLED,
    )
    publish(message.id, 'error', {'detail': '已停止生成'})


@shared_task(bind=True, max_retries=0, time_limit=180)
def run_assistant_chat(
    self,
    user_id: int,
    session_id: str,
    assistant_message_id: str,
    user_message_id: str,
    show_bql: bool = False,
    deep_think: bool = False,
) -> None:
    User = get_user_model()
    message_uuid = UUID(assistant_message_id)
    reset_stream(message_uuid)

    try:
        user = User.objects.get(id=user_id)
        session = ChatSession.objects.get(id=session_id, user=user)
        message = ChatMessage.objects.get(
            id=assistant_message_id,
            session=session,
            role=ChatMessage.ROLE_ASSISTANT,
        )
        user_message = ChatMessage.objects.get(
            id=user_message_id,
            session=session,
            role=ChatMessage.ROLE_USER,
        )
    except Exception as exc:
        logger.exception('Assistant task setup failed')
        try:
            message = ChatMessage.objects.get(id=assistant_message_id)
            _finalize_error(message, f'任务启动失败: {exc}')
        except ChatMessage.DoesNotExist:
            pass
        return

    llm_messages = build_llm_messages(session)
    service = AssistantService(user, deep_think=deep_think)
    accumulator = StreamAccumulator()
    last_persist = 0.0

    def maybe_persist(force: bool = False) -> None:
        nonlocal last_persist
        now = time.monotonic()
        if force or (now - last_persist) >= PERSIST_INTERVAL_SECONDS:
            _persist_from_accumulator(
                message,
                accumulator,
                generation_status=ChatMessage.STATUS_GENERATING,
            )
            message.refresh_from_db()
            last_persist = now

    try:
        for event in service._iter_chat_events(llm_messages, show_bql=show_bql):
            if is_cancelled(message_uuid):
                _finalize_cancelled(message, accumulator)
                return

            if event.event not in ('done', 'error'):
                publish(message_uuid, event.event, event.data)
            accumulator.apply(event)

            if event.event in ('tool_end', 'done', 'error'):
                maybe_persist(force=True)
            elif event.event in ('delta', 'reasoning_delta', 'thinking_set', 'status'):
                maybe_persist()

            if event.event == 'done':
                _finalize_done(message, session, user_message, accumulator, event.data)
                return

            if event.event == 'error':
                _finalize_error(message, event.data.get('detail', '助手响应失败'))
                return

        _finalize_error(message, '助手响应未完成，请重试')
    except (ValueError, LedgerNotFoundError) as exc:
        _finalize_error(message, str(exc))
    except Exception as exc:
        logger.exception('Assistant background task failed')
        _finalize_error(message, f'AI 助手暂时不可用: {exc}')
