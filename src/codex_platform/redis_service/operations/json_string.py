"""
codex_platform.redis_service.operations.json_string
====================================================
JSON operations via standard Redis string commands (SET / GET).

Works with any Redis instance — no server modules required.
Values are serialized with ``json.dumps`` and deserialized with ``json.loads``.
"""

import json
import logging
from typing import Any

from redis.asyncio import Redis

from codex_platform.redis_service.base import catch_redis_errors

log = logging.getLogger(__name__)


class JsonStringOperations:
    """Store JSON objects as Redis strings using SET/GET with json.dumps/loads.

    Works with any standard Redis instance — no server modules required.
    Does not support path-based access; for that use
    :class:`~codex_platform.redis_service.operations.json_module.JsonModuleOperations`.

    Example::

        svc = JsonStringOperations(client)
        await svc.set("user:42", {"name": "Alice", "age": 30}, ttl=3600)
        user = await svc.get("user:42")  # {"name": "Alice", "age": 30}
    """

    def __init__(self, client: Redis) -> None:
        self.client = client

    @catch_redis_errors
    async def set(self, key: str, obj: Any, ttl: int | None = None) -> None:
        """Serialize an object to JSON and store it in Redis (SET).

        Args:
            key: Redis key string.
            obj: Any JSON-serializable object (dict, list, str, int, …).
            ttl: Expiry in seconds. ``None`` means no expiry.

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        value = json.dumps(obj, ensure_ascii=False)
        await self.client.set(key, value, ex=ttl)
        log.debug("JsonStringOps | set key='%s' ttl=%s", key, ttl)

    @catch_redis_errors
    async def get(self, key: str) -> Any:
        """Read a Redis string and deserialize it from JSON (GET).

        Args:
            key: Redis key string.

        Returns:
            Deserialized object, or ``None`` if the key does not exist.

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        raw = await self.client.get(key)
        if raw is None:
            return None
        return json.loads(raw)

    @catch_redis_errors
    async def set_nx(self, key: str, obj: Any, ttl: int | None = None) -> bool:
        """Set a JSON value only if the key does not exist (SET NX).

        Args:
            key: Redis key string.
            obj: Any JSON-serializable object.
            ttl: Expiry in seconds. ``None`` means no expiry.

        Returns:
            ``True`` if the value was set, ``False`` if the key already existed.

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        value = json.dumps(obj, ensure_ascii=False)
        result = await self.client.set(key, value, ex=ttl, nx=True)
        log.debug("JsonStringOps | set_nx key='%s' result=%s", key, bool(result))
        return bool(result)

    @catch_redis_errors
    async def mget(self, *keys: str) -> list[Any]:
        """Retrieve multiple JSON values in a single request (MGET).

        Args:
            *keys: Redis key strings.

        Returns:
            List of deserialized objects in the same order as ``keys``.
            ``None`` for keys that do not exist.

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        if not keys:
            return []
        raws = await self.client.mget(*keys)
        return [json.loads(r) if r is not None else None for r in raws]
