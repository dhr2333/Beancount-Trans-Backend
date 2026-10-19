"""Copilot 流式事件日志（cache），支持 SSE 断线重连。"""
from __future__ import annotations

import time
from collections.abc import Callable, Iterator
from typing import Any
from uuid import UUID

from django.conf import settings
from django.core.cache import cache

STREAM_TTL = 3600
POLL_INTERVAL = 0.2
DEFAULT_MAX_WAIT_SECONDS = 960.0
DEFAULT_HEARTBEAT_SECONDS = 30.0


def _stream_key(message_id: UUID | str) -> str:
    return f'assistant:stream:{message_id}'


def _cancel_key(message_id: UUID | str) -> str:
    return f'assistant:cancel:{message_id}'


def _setting_seconds(name: str, default: float) -> float:
    try:
        return float(getattr(settings, name, default))
    except (TypeError, ValueError):
        return default


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
    max_wait_seconds: float | None = None,
    heartbeat_interval: float | None = None,
) -> Iterator[tuple[str, dict[str, Any]]]:
    """从 offset 0 轮询事件日志，直到终态或超时。

    长任务（25+ 条 BQL 的多轮工具调用）可能持续数分钟，期间通过心跳保持
    SSE 连接，避免 Nginx 与客户端空闲超时提前断开。
    """
    if max_wait_seconds is None:
        max_wait_seconds = _setting_seconds(
            'ASSISTANT_STREAM_MAX_WAIT_SECONDS',
            DEFAULT_MAX_WAIT_SECONDS,
        )
    if heartbeat_interval is None:
        heartbeat_interval = _setting_seconds(
            'ASSISTANT_STREAM_HEARTBEAT_SECONDS',
            DEFAULT_HEARTBEAT_SECONDS,
        )

    offset = 0
    now = time.monotonic()
    deadline = now + max_wait_seconds
    last_emit_at = now

    while True:
        for item in read_from(message_id, offset):
            offset += 1
            last_emit_at = time.monotonic()
            yield item['event'], item['data']
            if item['event'] in ('done', 'error'):
                return

        if is_terminal():
            # 任务先落库终态、再发布 done/error：补读一次，避免漏掉刚发布的事件。
            if poll_interval > 0:
                time.sleep(poll_interval)
            for item in read_from(message_id, offset):
                offset += 1
                yield item['event'], item['data']
                if item['event'] in ('done', 'error'):
                    return
            return

        now = time.monotonic()
        if now >= deadline:
            return
        if heartbeat_interval > 0 and now - last_emit_at >= heartbeat_interval:
            last_emit_at = now
            yield 'heartbeat', {'ts': int(time.time())}
        time.sleep(poll_interval)
