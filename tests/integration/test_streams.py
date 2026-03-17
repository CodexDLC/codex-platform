"""
Integration tests for Redis Streams (StreamProducer + StreamConsumer).

Uses a real Redis instance. Each test gets an isolated stream name to avoid
cross-test pollution. The `clean_redis` fixture flushes the DB after each test.

Covers:
- StreamProducer.add_event() → event ID returned
- StreamConsumer.ensure_group() → idempotent
- StreamConsumer.read() → returns StreamEvent with correct type and data
- StreamConsumer.ack() → clears the Pending Entries List (PEL)
"""

import pytest
from redis.asyncio import Redis

from codex_platform.streams.consumer import StreamConsumer
from codex_platform.streams.producer import StreamProducer


STREAM = "integration:stream:test"
GROUP = "test_group"
CONSUMER = "test_consumer"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _producer(client: Redis, stream: str = STREAM) -> StreamProducer:
    return StreamProducer(client, stream)


def _consumer(client: Redis, stream: str = STREAM) -> StreamConsumer:
    return StreamConsumer(client, stream, GROUP, CONSUMER)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_producer_add_event_returns_id(clean_redis: Redis) -> None:
    """add_event() returns a non-empty Redis Stream ID string."""
    producer = _producer(clean_redis)
    event_id = await producer.add_event("test_event", {"key": "value"})

    assert isinstance(event_id, str)
    assert len(event_id) > 0
    # Redis Stream IDs have the format "{timestamp}-{seq}"
    assert "-" in event_id


@pytest.mark.integration
async def test_producer_sanitizes_none_values(clean_redis: Redis) -> None:
    """add_event() silently drops None values from the payload."""
    producer = _producer(clean_redis)
    consumer = _consumer(clean_redis)
    await consumer.ensure_group()

    await producer.add_event("nullable_event", {"present": "yes", "missing": None})
    events = await consumer.read(count=1)

    assert len(events) == 1
    assert "missing" not in events[0].data
    assert events[0].data["present"] == "yes"


@pytest.mark.integration
async def test_consumer_ensure_group_is_idempotent(clean_redis: Redis) -> None:
    """ensure_group() can be called multiple times without raising."""
    consumer = _consumer(clean_redis)
    await consumer.ensure_group()
    await consumer.ensure_group()  # must not raise BUSYGROUP


@pytest.mark.integration
async def test_producer_consumer_roundtrip(clean_redis: Redis) -> None:
    """Full round-trip: produce an event and consume it with correct data."""
    producer = _producer(clean_redis)
    consumer = _consumer(clean_redis)
    await consumer.ensure_group()

    event_data = {"order_id": "42", "status": "pending"}
    await producer.add_event("order_created", event_data)

    events = await consumer.read(count=10)

    assert len(events) == 1
    event = events[0]
    assert event.event_type == "order_created"
    assert event.data["order_id"] == "42"
    assert event.data["status"] == "pending"


@pytest.mark.integration
async def test_consumer_read_empty_returns_empty_list(clean_redis: Redis) -> None:
    """read() on an empty stream returns [] without raising."""
    consumer = _consumer(clean_redis)
    await consumer.ensure_group()

    events = await consumer.read(count=10)

    assert events == []


@pytest.mark.integration
async def test_consumer_ack_clears_pel(clean_redis: Redis) -> None:
    """After ack(), the event is removed from the Pending Entries List."""
    producer = _producer(clean_redis)
    consumer = _consumer(clean_redis)
    await consumer.ensure_group()

    await producer.add_event("ack_test", {"x": "1"})
    events = await consumer.read(count=1)
    assert len(events) == 1

    # Before ACK: PEL should contain 1 entry
    pending_before = await clean_redis.xpending(STREAM, GROUP)
    assert pending_before["pending"] == 1

    # ACK
    await consumer.ack(events[0].id)

    # After ACK: PEL should be empty
    pending_after = await clean_redis.xpending(STREAM, GROUP)
    assert pending_after["pending"] == 0


@pytest.mark.integration
async def test_multiple_events_ordering(clean_redis: Redis) -> None:
    """Multiple events are delivered in insertion order."""
    producer = _producer(clean_redis)
    consumer = _consumer(clean_redis)
    await consumer.ensure_group()

    for i in range(3):
        await producer.add_event("seq_event", {"seq": str(i)})

    events = await consumer.read(count=10)

    assert len(events) == 3
    seqs = [e.data["seq"] for e in events]
    assert seqs == ["0", "1", "2"]
