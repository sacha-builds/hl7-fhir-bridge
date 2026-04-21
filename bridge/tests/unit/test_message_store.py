import asyncio

import pytest

from bridge.store import MessageRecord, MessageStore, ResourceRecord


def _record(msg_id: str, code: str = "AA") -> MessageRecord:
    return MessageRecord(
        id=msg_id,
        received_at="2026-04-20T12:00:00+00:00",
        message_type="ADT^A01",
        raw_v2="MSH|...",
        ack="MSH|...",
        ack_code=code,
        resources=[ResourceRecord("Patient", "create", "urn:id:H|1", {"resourceType": "Patient"})],
    )


@pytest.mark.asyncio
async def test_add_and_list_returns_newest_first() -> None:
    store = MessageStore()
    await store.add(_record("a"))
    await store.add(_record("b"))
    await store.add(_record("c"))

    ids = [m["id"] for m in store.list_summaries()]
    assert ids == ["c", "b", "a"]


@pytest.mark.asyncio
async def test_get_returns_full_detail() -> None:
    store = MessageStore()
    record = _record("x")
    await store.add(record)
    detail = store.get("x")
    assert detail is not None
    assert detail.message_type == "ADT^A01"
    assert detail.resources[0].resource_type == "Patient"


@pytest.mark.asyncio
async def test_ring_buffer_drops_oldest_when_full() -> None:
    store = MessageStore(max_messages=2)
    await store.add(_record("1"))
    await store.add(_record("2"))
    await store.add(_record("3"))

    ids = [m["id"] for m in store.list_summaries()]
    assert ids == ["3", "2"]
    assert store.get("1") is None
    assert store.get("3") is not None


@pytest.mark.asyncio
async def test_subscribers_receive_events_for_new_messages() -> None:
    store = MessageStore()
    received: list[dict] = []

    async def consume() -> None:
        async for event in store.subscribe():
            received.append(event)
            if len(received) == 2:
                return

    task = asyncio.create_task(consume())
    # Give the subscriber a tick to register
    await asyncio.sleep(0)
    await store.add(_record("one"))
    await store.add(_record("two"))
    await asyncio.wait_for(task, timeout=1.0)

    assert len(received) == 2
    assert received[0]["event"] == "message.received"
    assert received[0]["data"]["id"] == "one"
    assert received[1]["data"]["id"] == "two"
