"""
codex_platform.streams.producer
=======================================
Redis Stream producer — writes events via XADD.
"""

import logging
from typing import Any

from redis.asyncio import Redis
from redis.exceptions import ConnectionError, RedisError, TimeoutError

from codex_platform.redis_service.exceptions import RedisConnectionError, RedisServiceError

log = logging.getLogger(__name__)


class StreamProducer:
    """Writes events to a Redis Stream (XADD).

    Automatically sanitizes the payload before writing:
    - ``bool`` values are converted to ``"True"`` / ``"False"``
    - ``None`` values are filtered out
    - all remaining values are coerced to ``str``
    """

    def __init__(self, client: Redis, stream_name: str) -> None:
        self.client = client
        self.stream_name = stream_name

    async def add_event(self, event_type: str, data: dict[str, Any]) -> str:
        """Append an event to the Redis Stream (XADD).

        Args:
            event_type: Event type label, e.g. ``"new_appointment"`` or ``"new_contact"``.
            data: Event payload. ``None`` values are filtered out automatically.

        Returns:
            The ID of the newly added stream entry (e.g. ``"1718000000000-0"``).

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        payload = self._sanitize({"type": event_type, **data})
        try:
            result = await self.client.xadd(self.stream_name, payload)
            log.info("StreamProducer | added event_type='%s' id='%s' stream='%s'", event_type, result, self.stream_name)
            return str(result)
        except (ConnectionError, TimeoutError) as e:
            raise RedisConnectionError(f"Stream producer connection failed: {e}") from e
        except RedisError as e:
            raise RedisServiceError(f"Stream producer error: {e}") from e

    @staticmethod
    def _sanitize(data: dict[str, Any]) -> dict[str, str]:
        """Convert all values to str and filter out None entries."""
        return {
            k: ("True" if v is True else "False" if v is False else str(v)) for k, v in data.items() if v is not None
        }
