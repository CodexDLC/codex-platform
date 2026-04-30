"""
codex_platform.streams.producer
=======================================
Redis Stream producer — writes events via XADD.
"""

import contextlib
import json
import logging
import math
import uuid
from typing import Any

from redis.asyncio import Redis
from redis.exceptions import ConnectionError, RedisError, TimeoutError

from codex_platform.redis_service.exceptions import RedisConnectionError, RedisServiceError
from codex_platform.streams.codec import decode_stream_value, encode_stream_payload

log = logging.getLogger(__name__)


class StreamReplyTimeoutError(RedisServiceError):
    """Raised when a request/reply stream call does not receive a reply in time."""


class StreamProducer:
    """Writes events to a Redis Stream (XADD).

    Encodes structured payload values as JSON-prefixed Redis Stream fields.
    """

    def __init__(self, client: Redis, stream_name: str) -> None:
        self.client = client
        self.stream_name = stream_name

    async def publish(
        self,
        event_type: str,
        data: dict[str, Any],
        *,
        correlation_id: str | None = None,
    ) -> str:
        """Append an event to the Redis Stream (XADD).

        Args:
            event_type: Event type label, e.g. ``"new_appointment"`` or ``"new_contact"``.
            data: Event payload.
            correlation_id: Optional request/reply correlation id.

        Returns:
            The ID of the newly added stream entry (e.g. ``"1718000000000-0"``).

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        payload_data = {"type": event_type, **data}
        if correlation_id is not None:
            payload_data["correlation_id"] = correlation_id
        payload = self._sanitize(payload_data)
        try:
            result = await self.client.xadd(self.stream_name, payload)
            log.info("StreamProducer | added event_type='%s' id='%s' stream='%s'", event_type, result, self.stream_name)
            return str(result)
        except (ConnectionError, TimeoutError) as e:
            raise RedisConnectionError(f"Stream producer connection failed: {e}") from e
        except RedisError as e:
            raise RedisServiceError(f"Stream producer error: {e}") from e

    async def request(
        self,
        event_type: str,
        data: dict[str, Any],
        *,
        timeout: float = 30.0,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        """Publish an event and wait for a basic Redis-list reply.

        Replies are read from ``reply:{correlation_id}`` using ``BRPOP``.
        """
        cid = correlation_id or str(uuid.uuid4())
        await self.publish(event_type, data, correlation_id=cid)
        reply_key = f"reply:{cid}"
        try:
            result = await self.client.brpop(reply_key, timeout=max(1, math.ceil(timeout)))
        except (ConnectionError, TimeoutError) as e:
            raise RedisConnectionError(f"Stream reply connection failed: {e}") from e
        except RedisError as e:
            raise RedisServiceError(f"Stream reply error: {e}") from e
        if result is None:
            raise StreamReplyTimeoutError(f"Timed out waiting for stream reply: {reply_key}")
        _key, raw_value = result
        value = decode_stream_value(raw_value)
        if isinstance(value, str):
            with contextlib.suppress(json.JSONDecodeError):
                value = json.loads(value)
        if not isinstance(value, dict):
            raise RedisServiceError(f"Stream reply must decode to dict, got {type(value).__name__}")
        return value

    async def publish_reply(
        self,
        correlation_id: str,
        data: dict[str, Any],
        *,
        ttl: int | None = None,
    ) -> int:
        """Publish a basic request/reply response to ``reply:{correlation_id}``."""
        reply_key = f"reply:{correlation_id}"
        encoded = encode_stream_payload({"reply": data})["reply"]
        try:
            length = await self.client.lpush(reply_key, encoded)
            if ttl is not None:
                await self.client.expire(reply_key, ttl)
            return int(length)
        except (ConnectionError, TimeoutError) as e:
            raise RedisConnectionError(f"Stream reply publish connection failed: {e}") from e
        except RedisError as e:
            raise RedisServiceError(f"Stream reply publish error: {e}") from e

    async def add_event(self, event_type: str, data: dict[str, Any]) -> str:
        """Compatibility alias for :meth:`publish`."""
        return await self.publish(event_type, data)

    @staticmethod
    def _sanitize(data: dict[str, Any]) -> dict[str, str]:
        """Encode all values for Redis Stream storage."""
        return encode_stream_payload(data)
