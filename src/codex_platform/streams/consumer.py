"""
codex_platform.streams.consumer
=======================================
Redis Stream consumer — reads events via XREADGROUP, acknowledges via XACK.
"""

import logging
from dataclasses import dataclass
from typing import Any

from redis.asyncio import Redis
from redis.exceptions import ConnectionError, RedisError, TimeoutError

from codex_platform.redis_service.exceptions import RedisConnectionError, RedisServiceError
from codex_platform.streams.codec import decode_stream_payload

log = logging.getLogger(__name__)


@dataclass
class StreamEvent:
    """Parsed Redis Stream event."""

    id: str
    event_type: str
    data: dict[str, Any]

    @property
    def payload(self) -> dict[str, Any]:
        """Return dispatcher-ready payload with the ``type`` field restored."""
        return {"type": self.event_type, **self.data}


class StreamConsumer:
    """Reads events from a Redis Stream via a consumer group (XREADGROUP).

    Acknowledges processed messages via XACK.
    """

    def __init__(self, client: Redis, stream_name: str, group: str, consumer: str) -> None:
        self.client = client
        self.stream_name = stream_name
        self.group = group
        self.consumer = consumer

    async def ensure_group(self) -> None:
        """Create the consumer group if it does not already exist (XGROUP CREATE … MKSTREAM)."""
        try:
            await self.client.xgroup_create(self.stream_name, self.group, id="0", mkstream=True)
            log.info("StreamConsumer | group created stream='%s' group='%s'", self.stream_name, self.group)
        except RedisError as e:
            if "BUSYGROUP" in str(e):
                log.debug("StreamConsumer | group already exists stream='%s' group='%s'", self.stream_name, self.group)
            else:
                raise RedisServiceError(f"Failed to create group: {e}") from e

    async def create_group(self, stream_name: str | None = None, group_name: str | None = None) -> None:
        """Create a group using the ``StreamStorageProtocol`` method name."""
        original_stream = self.stream_name
        original_group = self.group
        if stream_name is not None:
            self.stream_name = stream_name
        if group_name is not None:
            self.group = group_name
        try:
            await self.ensure_group()
        finally:
            self.stream_name = original_stream
            self.group = original_group

    async def read(self, count: int = 10) -> list[StreamEvent]:
        """Read new events from the stream for the consumer group (XREADGROUP).

        Args:
            count: Maximum number of messages to fetch per call. Defaults to ``10``.

        Returns:
            List of :class:`StreamEvent` instances. Empty list if no new messages.

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        try:
            raw = await self.client.xreadgroup(
                groupname=self.group,
                consumername=self.consumer,
                streams={self.stream_name: ">"},
                count=count,
            )
            if not raw:
                return []
            events = [self._parse(msg_id, fields) for msg_id, fields in raw[0][1]]
            log.debug("StreamConsumer | read count=%d stream='%s'", len(events), self.stream_name)
            return events
        except (ConnectionError, TimeoutError) as e:
            raise RedisConnectionError(f"Stream consumer connection failed: {e}") from e
        except RedisError as e:
            raise RedisServiceError(f"Stream consumer error: {e}") from e

    async def read_events(
        self,
        stream_name: str | None = None,
        group_name: str | None = None,
        consumer_name: str | None = None,
        count: int = 10,
    ) -> list[tuple[str, dict[str, Any]]]:
        """Read dispatcher-ready events using the ``StreamStorageProtocol`` method name."""
        original_stream = self.stream_name
        original_group = self.group
        original_consumer = self.consumer
        if stream_name is not None:
            self.stream_name = stream_name
        if group_name is not None:
            self.group = group_name
        if consumer_name is not None:
            self.consumer = consumer_name
        try:
            events = await self.read(count=count)
            return [(event.id, event.payload) for event in events]
        finally:
            self.stream_name = original_stream
            self.group = original_group
            self.consumer = original_consumer

    async def ack(self, event_id: str) -> None:
        """Acknowledge that an event has been processed (XACK).

        Args:
            event_id: Stream entry ID returned by :meth:`read`.

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        try:
            await self.client.xack(self.stream_name, self.group, event_id)
            log.debug("StreamConsumer | ack id='%s' stream='%s'", event_id, self.stream_name)
        except (ConnectionError, TimeoutError) as e:
            raise RedisConnectionError(f"Stream ack connection failed: {e}") from e
        except RedisError as e:
            raise RedisServiceError(f"Stream ack error: {e}") from e

    async def ack_event(self, stream_name: str, group_name: str, message_id: str) -> None:
        """Acknowledge an event using the ``StreamStorageProtocol`` method name."""
        original_stream = self.stream_name
        original_group = self.group
        self.stream_name = stream_name
        self.group = group_name
        try:
            await self.ack(message_id)
        finally:
            self.stream_name = original_stream
            self.group = original_group

    @staticmethod
    def _parse(msg_id: Any, fields: dict[bytes | str, bytes | str]) -> StreamEvent:
        data = decode_stream_payload(fields)
        event_type = data.pop("type", "unknown")
        return StreamEvent(id=str(msg_id), event_type=event_type, data=data)
