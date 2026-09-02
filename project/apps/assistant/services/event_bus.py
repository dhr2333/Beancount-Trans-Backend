"""Copilot 流式事件日志（cache），支持 SSE 断线重连。"""
from __future__ import annotations

import time
from collections.abc import Callable, Iterator
from typing import Any
from uuid import UUID

from django.core.cache import cache

STREAM_TTL = 3600
POLL_INTERVAL = 0.2


def _stream_key(message_id: UUID | str) -> str:
    return f'assistant:stream:{message_id}'


def _cancel_key(message_id: UUID | str) -> str:
    return f'assistant:cancel:{message_id}'


def reset_stream(message_id: UUID | str) -> None:
    cache.delete(_stream_key(message_id))
    cache.delete(_cancel_key(message_id))


def publish(message_id: UUID | str, event: str, data: dict[str, Any]) -> None:
    key = _stream_key(message_id)
    events: list[dict[str, Any]] = cache.get(key) or []
    events.append({'event': event, 'data': data})
    cache.set(key, events, STREAM_TTL)


def read_from(message_id: UUID | str, offset: int = 0) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = cache.get(_stream_key(message_id)) or []
    return events[offset:]


def request_cancel(message_id: UUID | str) -> None:
    cache.set(_cancel_key(message_id), True, STREAM_TTL)


def is_cancelled(message_id: UUID | str) -> bool:
    return bool(cache.get(_cancel_key(message_id)))


def iter_subscribe_events(
    message_id: UUID | str,
    *,
    is_terminal: Callable[[], bool],
    poll_interval: float = POLL_INTERVAL,
    max_wait_seconds: float = 180.0,
) -> Iterator[tuple[str, dict[str, Any]]]:
    """从 offset 0 轮询事件日志，直到终态或超时。"""
    offset = 0
    deadline = time.monotonic() + max_wait_seconds
    while True:
        batch = read_from(message_id, offset)
        for item in batch:
            offset += 1
            yield item['event'], item['data']
            if item['event'] in ('done', 'error'):
                return
        if is_terminal():
            return
        if time.monotonic() >= deadline:
            return
        time.sleep(poll_interval)
