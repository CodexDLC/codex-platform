"""Tests for codex_platform.streams.producer.StreamProducer."""

import pytest
from redis.exceptions import RedisError

from codex_platform.redis_service.exceptions import RedisConnectionError, RedisServiceError
from codex_platform.streams.producer import StreamProducer, StreamReplyTimeoutError

pytestmark = pytest.mark.unit


class TestAddEvent:
    """StreamProducer.add_event writes to stream."""

    async def test_add_event_writes_to_stream(self, redis_client):
        producer = StreamProducer(redis_client, "test:stream")
        msg_id = await producer.add_event("order.created", {"order_id": "123"})

        assert isinstance(msg_id, str)
        assert msg_id  # non-empty

        # Verify data in the stream
        entries = await redis_client.xrange("test:stream")
        assert len(entries) == 1
        _, fields = entries[0]
        assert fields["type"] == "order.created"
        assert fields["order_id"] == "123"

    async def test_add_event_returns_message_id(self, redis_client):
        producer = StreamProducer(redis_client, "test:stream")
        msg_id = await producer.add_event("ping", {})
        # Redis stream IDs contain a dash: e.g. "1234567890-0"
        assert "-" in msg_id


class TestPublish:
    async def test_publish_adds_correlation_id(self, redis_client):
        producer = StreamProducer(redis_client, "test:stream")
        await producer.publish("ping", {}, correlation_id="cid-1")

        entries = await redis_client.xrange("test:stream")
        assert entries[0][1]["correlation_id"] == "cid-1"


class TestSanitize:
    """StreamProducer._sanitize data conversion."""

    def test_bool_true_json_encoded(self):
        result = StreamProducer._sanitize({"active": True})
        assert result["active"] == "json:true"

    def test_bool_false_json_encoded(self):
        result = StreamProducer._sanitize({"active": False})
        assert result["active"] == "json:false"

    def test_none_values_json_encoded(self):
        result = StreamProducer._sanitize({"a": "1", "b": None, "c": "3"})
        assert result == {"a": "1", "b": "json:null", "c": "3"}

    def test_numeric_values_json_encoded(self):
        result = StreamProducer._sanitize({"count": 42, "price": 9.99})
        assert result["count"] == "json:42"
        assert result["price"] == "json:9.99"

    def test_dict_and_list_values_json_encoded(self):
        result = StreamProducer._sanitize({"changes": {"hp": -1}, "ids": [1, 2]})
        assert result["changes"] == 'json:{"hp":-1}'
        assert result["ids"] == "json:[1,2]"

    def test_mixed_types(self):
        result = StreamProducer._sanitize(
            {
                "name": "test",
                "active": True,
                "deleted": False,
                "extra": None,
                "count": 5,
            }
        )
        assert result == {
            "name": "test",
            "active": "json:true",
            "deleted": "json:false",
            "extra": "json:null",
            "count": "json:5",
        }


class TestRequestReply:
    async def test_request_returns_reply_dict(self, redis_client):
        producer = StreamProducer(redis_client, "test:stream")
        await producer.publish_reply("cid-1", {"status": "ok"})

        result = await producer.request("ping", {}, correlation_id="cid-1", timeout=1)

        assert result == {"status": "ok"}

    async def test_request_times_out(self, redis_client):
        producer = StreamProducer(redis_client, "test:stream")

        with pytest.raises(StreamReplyTimeoutError):
            await producer.request("ping", {}, correlation_id="missing", timeout=0.01)


class TestErrorHandling:
    """Exception wrapping for Redis errors."""

    async def test_connection_error_raises_redis_connection_error(self, monkeypatch, redis_client):
        producer = StreamProducer(redis_client, "test:stream")

        async def broken_xadd(*args, **kwargs):
            from redis.exceptions import ConnectionError

            raise ConnectionError("connection lost")

        monkeypatch.setattr(redis_client, "xadd", broken_xadd)

        with pytest.raises(RedisConnectionError):
            await producer.add_event("ping", {})

    async def test_redis_error_raises_redis_service_error(self, monkeypatch, redis_client):
        producer = StreamProducer(redis_client, "test:stream")

        async def broken_xadd(*args, **kwargs):
            raise RedisError("unexpected redis error")

        monkeypatch.setattr(redis_client, "xadd", broken_xadd)

        with pytest.raises(RedisServiceError):
            await producer.add_event("ping", {})
