"""
codex_platform.redis_service.operations.list_
==============================================
Redis List operations.
"""

import logging
from typing import Any

from redis.asyncio import Redis

from codex_platform.redis_service.base import catch_redis_errors
from codex_platform.redis_service.keys import BaseRedisKey, resolve_key

log = logging.getLogger(__name__)


class ListOperations:
    """Redis List operations (RPUSH / LPUSH / LPOP / LRANGE and more).

    Accepts an already-constructed ``redis.asyncio.Redis`` client.
    All methods wrap Redis errors in typed exceptions.

    Example::

        ops = ListOperations(client)
        await ops.push("queue:jobs", "job-1", "job-2")
        job = await ops.pop("queue:jobs")
    """

    def __init__(self, client: Redis) -> None:
        self.client = client

    @catch_redis_errors
    async def push(self, key: "str | BaseRedisKey", *values: str, **kwargs: Any) -> int:
        """Append one or more values to the end of a list (RPUSH).

        Args:
            key: Redis key or a ``BaseRedisKey`` instance.
            *values: String values to append.
            **kwargs: Extra parameters forwarded to ``resolve_key``.

        Returns:
            New length of the list after the operation.

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        real_key = resolve_key(key, **kwargs)
        return int(await self.client.rpush(real_key, *values))

    @catch_redis_errors
    async def lpush(self, key: "str | BaseRedisKey", *values: str, **kwargs: Any) -> int:
        """Prepend one or more values to the beginning of a list (LPUSH).

        Args:
            key: Redis key or a ``BaseRedisKey`` instance.
            *values: String values to prepend.
            **kwargs: Extra parameters forwarded to ``resolve_key``.

        Returns:
            New length of the list after the operation.

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        real_key = resolve_key(key, **kwargs)
        return int(await self.client.lpush(real_key, *values))

    @catch_redis_errors
    async def pop(self, key: "str | BaseRedisKey", **kwargs: Any) -> str | None:
        """Remove and return the first element of a list (LPOP).

        Args:
            key: Redis key or a ``BaseRedisKey`` instance.
            **kwargs: Extra parameters forwarded to ``resolve_key``.

        Returns:
            The first element, or ``None`` if the list is empty or does not exist.

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        real_key = resolve_key(key, **kwargs)
        value = await self.client.lpop(real_key)
        return str(value) if value is not None else None

    @catch_redis_errors
    async def rpop(self, key: "str | BaseRedisKey", **kwargs: Any) -> str | None:
        """Remove and return the last element of a list (RPOP).

        Args:
            key: Redis key or a ``BaseRedisKey`` instance.
            **kwargs: Extra parameters forwarded to ``resolve_key``.

        Returns:
            The last element, or ``None`` if the list is empty or does not exist.

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        real_key = resolve_key(key, **kwargs)
        value = await self.client.rpop(real_key)
        return str(value) if value is not None else None

    @catch_redis_errors
    async def brpop(self, *keys: str, timeout: int = 0) -> tuple[str, str] | None:
        """Blocking pop of the last element from the first non-empty list (BRPOP).

        Args:
            *keys: One or more Redis key strings to check in order.
            timeout: Maximum seconds to block. ``0`` blocks indefinitely.

        Returns:
            ``(key, value)`` tuple when an element is available,
            or ``None`` if the timeout expires.

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        result = await self.client.brpop(list(keys), timeout=timeout)
        if result:
            return str(result[0]), str(result[1])
        return None

    @catch_redis_errors
    async def range(self, key: "str | BaseRedisKey", start: int = 0, end: int = -1, **kwargs: Any) -> list[str]:
        """Return a slice of list elements by index range (LRANGE).

        Args:
            key: Redis key or a ``BaseRedisKey`` instance.
            start: Start index (0-based). Negative values count from the end.
            end: End index inclusive. ``-1`` means the last element.
            **kwargs: Extra parameters forwarded to ``resolve_key``.

        Returns:
            List of elements in the requested range.

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        real_key = resolve_key(key, **kwargs)
        return await self.client.lrange(real_key, start, end)

    @catch_redis_errors
    async def length(self, key: "str | BaseRedisKey", **kwargs: Any) -> int:
        """Return the number of elements in a list (LLEN).

        Args:
            key: Redis key or a ``BaseRedisKey`` instance.
            **kwargs: Extra parameters forwarded to ``resolve_key``.

        Returns:
            List length. ``0`` if the key does not exist.

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        real_key = resolve_key(key, **kwargs)
        return int(await self.client.llen(real_key))

    @catch_redis_errors
    async def set_index(self, key: "str | BaseRedisKey", index: int, value: str, **kwargs: Any) -> None:
        """Set the element at a specific list index (LSET).

        Args:
            key: Redis key or a ``BaseRedisKey`` instance.
            index: Zero-based index. Negative values count from the end.
            value: New value to set at the given index.
            **kwargs: Extra parameters forwarded to ``resolve_key``.

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        real_key = resolve_key(key, **kwargs)
        await self.client.lset(real_key, index, value)

    @catch_redis_errors
    async def trim(self, key: "str | BaseRedisKey", start: int, end: int, **kwargs: Any) -> None:
        """Trim a list to the specified index range, discarding all other elements (LTRIM).

        Args:
            key: Redis key or a ``BaseRedisKey`` instance.
            start: Start index (inclusive).
            end: End index (inclusive).
            **kwargs: Extra parameters forwarded to ``resolve_key``.

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        real_key = resolve_key(key, **kwargs)
        await self.client.ltrim(real_key, start, end)

    @catch_redis_errors
    async def move(self, src: str, dst: str) -> str | None:
        """Atomically move the last element of ``src`` to the head of ``dst`` (RPOPLPUSH).

        Args:
            src: Source list key.
            dst: Destination list key.

        Returns:
            The moved element, or ``None`` if ``src`` is empty.

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        value = await self.client.rpoplpush(src, dst)
        return str(value) if value is not None else None
