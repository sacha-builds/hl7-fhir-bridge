"""In-memory ring buffer of processed v2 messages with pub/sub for WebSocket fan-out.

This is a demo-grade store — not durable, not clustered. Suitable for a
portfolio showcase where a reviewer should see live message flow, not
for production where you'd back this with Kafka/Redis Streams/etc.
"""

from __future__ import annotations

import asyncio
import uuid
from collections import deque
from collections.abc import AsyncIterator
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True)
class ResourceRecord:
    resource_type: str
    operation: str
    identifier_query: str | None
    resource: dict[str, Any]


@dataclass
class MessageRecord:
    id: str
    received_at: str
    message_type: str
    raw_v2: str
    ack: str
    ack_code: str
    resources: list[ResourceRecord] = field(default_factory=list)
    validation_issues: list[dict[str, str]] = field(default_factory=list)
    error: str | None = None

    def to_summary(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "received_at": self.received_at,
            "message_type": self.message_type,
            "ack_code": self.ack_code,
            "resource_count": len(self.resources),
            "error": self.error,
        }

    def to_detail(self) -> dict[str, Any]:
        data = asdict(self)
        return data


class MessageStore:
    def __init__(self, max_messages: int = 500) -> None:
        self._messages: deque[MessageRecord] = deque(maxlen=max_messages)
        self._by_id: dict[str, MessageRecord] = {}
        self._subscribers: set[asyncio.Queue[dict[str, Any]]] = set()
        self._lock = asyncio.Lock()

    async def add(self, record: MessageRecord) -> None:
        async with self._lock:
            if len(self._messages) == self._messages.maxlen:
                dropped = self._messages[0]
                self._by_id.pop(dropped.id, None)
            self._messages.append(record)
            self._by_id[record.id] = record
        payload = {"event": "message.received", "data": record.to_summary()}
        for queue in list(self._subscribers):
            queue.put_nowait(payload)

    def list_summaries(self, limit: int = 100) -> list[dict[str, Any]]:
        # newest first
        return [m.to_summary() for m in reversed(self._messages)][:limit]

    def get(self, message_id: str) -> MessageRecord | None:
        return self._by_id.get(message_id)

    async def clear(self) -> None:
        async with self._lock:
            self._messages.clear()
            self._by_id.clear()
        payload = {"event": "messages.cleared", "data": {}}
        for queue in list(self._subscribers):
            queue.put_nowait(payload)

    async def subscribe(self) -> AsyncIterator[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=256)
        self._subscribers.add(queue)
        try:
            while True:
                yield await queue.get()
        finally:
            self._subscribers.discard(queue)


def new_message_id() -> str:
    return uuid.uuid4().hex[:12]


def now_iso() -> str:
    return datetime.now(UTC).isoformat()
