"""Tests for codex_platform.streams.consumer.StreamConsumer and StreamEvent."""

import pytest

from codex_platform.streams.consumer import StreamConsumer, StreamEvent
from codex_platform.streams.processor import StreamStorageProtocol

pytestmark = pytest.mark.unit


class TestEnsureGroup:
    """StreamConsumer.ensure_group creates consumer group."""

    async def test_creates_group(self, redis_client):
        consumer = StreamConsumer(redis_client, "test:stream", "grp", "c1")
        await consumer.ensure_group()

        # Verify group exists by calling xinfo_groups
        groups = await redis_client.xinfo_groups("test:stream")
        group_names = [g["name"] for g in groups]
        assert "grp" in group_names

    async def test_idempotent_busygroup_handled(self, redis_client):
        consumer = StreamConsumer(redis_client, "test:stream", "grp", "c1")
        await consumer.ensure_group()
        # Second call should not raise (BUSYGROUP is silenced)
        await consumer.ensure_group()


class TestRead:
    """StreamConsumer.read returns StreamEvent list."""

    async def test_read_returns_events(self, redis_client):
        # Setup: create group, add a message
        consumer = StreamConsumer(redis_client, "test:stream", "grp", "c1")
        await consumer.ensure_group()
        await redis_client.xadd("test:stream", {"type": "order.paid", "order_id": "42"})

        events = await consumer.read(count=10)
        assert len(events) == 1
        assert isinstance(events[0], StreamEvent)
        assert events[0].event_type == "order.paid"
        assert events[0].data["order_id"] == "42"

    async def test_read_decodes_json_values(self, redis_client):
        consumer = StreamConsumer(redis_client, "test:stream", "grp", "c1")
        await consumer.ensure_group()
        await redis_client.xadd("test:stream", {"type": "changed", "changes": 'json:{"hp":-1}', "active": "json:true"})

        events = await consumer.read(count=10)

        assert events[0].data["changes"] == {"hp": -1}
        assert events[0].data["active"] is True

    async def test_read_returns_empty_when_no_messages(self, redis_client):
        consumer = StreamConsumer(redis_client, "test:stream", "grp", "c1")
        await consumer.ensure_group()

        events = await consumer.read(count=10, block_ms=1)
        assert events == []

    async def test_read_passes_block_to_xreadgroup(self):
        calls = []

        class FakeRedis:
            async def xreadgroup(self, **kwargs):
                calls.append(kwargs)
                return []

        consumer = StreamConsumer(FakeRedis(), "test:stream", "grp", "c1")

        events = await consumer.read(count=3, block_ms=5000)

        assert events == []
        assert calls == [
            {
                "groupname": "grp",
                "consumername": "c1",
                "streams": {"test:stream": ">"},
                "count": 3,
                "block": 5000,
            }
        ]

    async def test_read_can_keep_legacy_non_blocking_call(self):
        calls = []

        class FakeRedis:
            async def xreadgroup(self, **kwargs):
                calls.append(kwargs)
                return []

        consumer = StreamConsumer(FakeRedis(), "test:stream", "grp", "c1")

        await consumer.read(count=3, block_ms=None)

        assert "block" not in calls[0]


class TestAck:
    """StreamConsumer.ack acknowledges events."""

    async def test_ack_works(self, redis_client):
        consumer = StreamConsumer(redis_client, "test:stream", "grp", "c1")
        await consumer.ensure_group()
        await redis_client.xadd("test:stream", {"type": "ping"})

        events = await consumer.read(count=10)
        assert len(events) == 1

        # ACK should not raise
        await consumer.ack(events[0].id)

        # After ACK the pending list should be empty
        pending = await redis_client.xpending(
            "test:stream",
            "grp",
        )
        assert pending["pending"] == 0


class TestStorageProtocol:
    async def test_consumer_matches_storage_protocol(self, redis_client):
        consumer = StreamConsumer(redis_client, "test:stream", "grp", "c1")

        assert isinstance(consumer, StreamStorageProtocol)

    async def test_read_events_returns_dispatcher_payload(self, redis_client):
        consumer = StreamConsumer(redis_client, "test:stream", "grp", "c1")
        await consumer.create_group("test:stream", "grp")
        await redis_client.xadd("test:stream", {"type": "ping", "value": "json:42"})

        events = await consumer.read_events("test:stream", "grp", "c1", 10, block_ms=1)

        assert len(events) == 1
        message_id, payload = events[0]
        assert "-" in message_id
        assert payload == {"type": "ping", "value": 42}


class TestStreamEvent:
    """StreamEvent dataclass."""

    def test_fields(self):
        ev = StreamEvent(id="1-0", event_type="test", data={"k": "v"})
        assert ev.id == "1-0"
        assert ev.event_type == "test"
        assert ev.data == {"k": "v"}
