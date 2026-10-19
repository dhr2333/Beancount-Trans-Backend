"""Copilot 流式事件订阅：心跳与终态补读。"""
from __future__ import annotations

from uuid import uuid4

from project.apps.assistant.services import event_bus


def test_emits_heartbeat_while_idle():
    message_id = uuid4()
    calls = {'count': 0}

    def is_terminal() -> bool:
        calls['count'] += 1
        return calls['count'] >= 5

    events = list(event_bus.iter_subscribe_events(
        message_id,
        is_terminal=is_terminal,
        poll_interval=0.001,
        max_wait_seconds=1.0,
        heartbeat_interval=0.0001,
    ))

    assert any(name == 'heartbeat' for name, _data in events)


def test_done_event_ends_subscription():
    message_id = uuid4()
    event_bus.publish(message_id, 'done', {'reply': 'ok'})

    events = list(event_bus.iter_subscribe_events(
        message_id,
        is_terminal=lambda: True,
        poll_interval=0,
        max_wait_seconds=1.0,
        heartbeat_interval=0,
    ))

    assert events == [('done', {'reply': 'ok'})]


def test_flushes_terminal_event_published_after_terminal_check():
    message_id = uuid4()
    calls = {'count': 0}

    def is_terminal() -> bool:
        calls['count'] += 1
        if calls['count'] == 1:
            # 模拟数据库已终态，但 done 在终态检查之后才写入事件日志
            event_bus.publish(message_id, 'done', {'reply': 'late'})
        return True

    events = list(event_bus.iter_subscribe_events(
        message_id,
        is_terminal=is_terminal,
        poll_interval=0.001,
        max_wait_seconds=1.0,
        heartbeat_interval=0,
    ))

    assert events == [('done', {'reply': 'late'})]
