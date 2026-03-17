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

log = logging.getLogger(__name__)


@dataclass
class StreamEvent:
    """Parsed Redis Stream event."""

    id: str
    event_type: str
    data: dict[str, str]


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

    @staticmethod
    def _parse(msg_id: Any, fields: dict[bytes | str, bytes | str]) -> StreamEvent:
        data = {
            (k.decode() if isinstance(k, bytes) else k): (v.decode() if isinstance(v, bytes) else v)
            for k, v in fields.items()
        }
        event_type = data.pop("type", "unknown")
        return StreamEvent(id=str(msg_id), event_type=event_type, data=data)
