"""
codex_platform.redis_service.operations.string
===============================================
Redis String/Key operations.
"""

import logging
from typing import Any

from redis.asyncio import Redis

from codex_platform.redis_service.base import catch_redis_errors
from codex_platform.redis_service.keys import BaseRedisKey, resolve_key

log = logging.getLogger(__name__)


class StringOperations:
    """Redis String and key-level operations (SET / GET / EXPIRE / TTL and more).

    Accepts an already-constructed ``redis.asyncio.Redis`` client.
    All methods wrap Redis errors in typed exceptions.

    Example::

        ops = StringOperations(client)
        await ops.set("session:abc", "token-value", ttl=3600)
        token = await ops.get("session:abc")
    """

    def __init__(self, client: Redis) -> None:
        self.client = client

    @catch_redis_errors
    async def set(self, key: "str | BaseRedisKey", value: str, ttl: int | None = None, **kwargs: Any) -> None:
        """Set a string value (SET).

        Args:
            key: Redis key or a ``BaseRedisKey`` instance.
            value: String value to store.
            ttl: Expiry in seconds. ``None`` means no expiry.
            **kwargs: Extra parameters forwarded to ``resolve_key``.

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        real_key = resolve_key(key, **kwargs)
        await self.client.set(real_key, value, ex=ttl)

    @catch_redis_errors
    async def setnx(self, key: "str | BaseRedisKey", value: str, ttl: int | None = None, **kwargs: Any) -> bool:
        """Set a value only if the key does not exist (SET NX).

        Args:
            key: Redis key or a ``BaseRedisKey`` instance.
            value: String value to store.
            ttl: Expiry in seconds. ``None`` means no expiry.
            **kwargs: Extra parameters forwarded to ``resolve_key``.

        Returns:
            ``True`` if the value was set, ``False`` if the key already existed.

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        real_key = resolve_key(key, **kwargs)
        return bool(await self.client.set(real_key, value, ex=ttl, nx=True))

    @catch_redis_errors
    async def get(self, key: "str | BaseRedisKey", **kwargs: Any) -> str | None:
        """Retrieve a string value (GET).

        Args:
            key: Redis key or a ``BaseRedisKey`` instance.
            **kwargs: Extra parameters forwarded to ``resolve_key``.

        Returns:
            String value, or ``None`` if the key does not exist.

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        real_key = resolve_key(key, **kwargs)
        val = await self.client.get(real_key)
        return str(val) if val is not None else None

    @catch_redis_errors
    async def getset(self, key: "str | BaseRedisKey", value: str, **kwargs: Any) -> str | None:
        """Atomically set a new value and return the previous one (GETSET).

        Args:
            key: Redis key or a ``BaseRedisKey`` instance.
            value: New value to store.
            **kwargs: Extra parameters forwarded to ``resolve_key``.

        Returns:
            Previous value, or ``None`` if the key did not exist.

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        real_key = resolve_key(key, **kwargs)
        val = await self.client.getset(real_key, value)
        return str(val) if val is not None else None

    @catch_redis_errors
    async def mget(self, *keys: str) -> list[str | None]:
        """Retrieve values for multiple keys in a single request (MGET).

        Args:
            *keys: Redis key strings.

        Returns:
            List of values in the same order as ``keys``.
            ``None`` for keys that do not exist.

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        values = await self.client.mget(list(keys))
        return [str(v) if v is not None else None for v in values]

    @catch_redis_errors
    async def mset(self, mapping: dict[str, str]) -> None:
        """Set values for multiple keys in a single call (MSET).

        Args:
            mapping: Dict of ``{key: value}`` pairs to write.

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        await self.client.mset(mapping)

    @catch_redis_errors
    async def incr(self, key: "str | BaseRedisKey", **kwargs: Any) -> int:
        """Increment a numeric value by 1 (INCR).

        Args:
            key: Redis key or a ``BaseRedisKey`` instance.
            **kwargs: Extra parameters forwarded to ``resolve_key``.

        Returns:
            New value after incrementing.

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        real_key = resolve_key(key, **kwargs)
        return int(await self.client.incr(real_key))

    @catch_redis_errors
    async def incrby(self, key: "str | BaseRedisKey", amount: int, **kwargs: Any) -> int:
        """Increment a numeric value by a given amount (INCRBY).

        Args:
            key: Redis key or a ``BaseRedisKey`` instance.
            amount: Increment step.
            **kwargs: Extra parameters forwarded to ``resolve_key``.

        Returns:
            New value after incrementing.

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        real_key = resolve_key(key, **kwargs)
        return int(await self.client.incrby(real_key, amount))

    @catch_redis_errors
    async def append(self, key: "str | BaseRedisKey", value: str, **kwargs: Any) -> int:
        """Append a string to an existing value (APPEND).

        Args:
            key: Redis key or a ``BaseRedisKey`` instance.
            value: String to append.
            **kwargs: Extra parameters forwarded to ``resolve_key``.

        Returns:
            New total length of the value after appending.

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        real_key = resolve_key(key, **kwargs)
        return int(await self.client.append(real_key, value))

    @catch_redis_errors
    async def delete(self, key: "str | BaseRedisKey", **kwargs: Any) -> None:
        """Delete a key (DEL).

        Args:
            key: Redis key or a ``BaseRedisKey`` instance.
            **kwargs: Extra parameters forwarded to ``resolve_key``.

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        real_key = resolve_key(key, **kwargs)
        await self.client.delete(real_key)

    @catch_redis_errors
    async def delete_by_pattern(self, pattern: str) -> int:
        """Delete all keys matching a glob pattern (SCAN + DEL).

        Args:
            pattern: Glob pattern, e.g. ``"session:*"``.

        Returns:
            Number of keys deleted.

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        keys = [k async for k in self.client.scan_iter(match=pattern)]
        if not keys:
            return 0
        return int(await self.client.delete(*keys))

    @catch_redis_errors
    async def expire(self, key: "str | BaseRedisKey", ttl: int, **kwargs: Any) -> bool:
        """Set a TTL (expiry) on a key in seconds (EXPIRE).

        Args:
            key: Redis key or a ``BaseRedisKey`` instance.
            ttl: Time-to-live in seconds.
            **kwargs: Extra parameters forwarded to ``resolve_key``.

        Returns:
            ``True`` if the TTL was set, ``False`` if the key does not exist.

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        real_key = resolve_key(key, **kwargs)
        return bool(await self.client.expire(real_key, ttl))

    @catch_redis_errors
    async def ttl(self, key: "str | BaseRedisKey", **kwargs: Any) -> int:
        """Return the remaining TTL of a key in seconds (TTL).

        Args:
            key: Redis key or a ``BaseRedisKey`` instance.
            **kwargs: Extra parameters forwarded to ``resolve_key``.

        Returns:
            Remaining TTL in seconds. ``-1`` if no TTL is set, ``-2`` if the key does not exist.

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        real_key = resolve_key(key, **kwargs)
        return int(await self.client.ttl(real_key))

    @catch_redis_errors
    async def exists(self, key: "str | BaseRedisKey", **kwargs: Any) -> bool:
        """Check whether a key exists (EXISTS).

        Args:
            key: Redis key or a ``BaseRedisKey`` instance.
            **kwargs: Extra parameters forwarded to ``resolve_key``.

        Returns:
            ``True`` if the key exists, ``False`` otherwise.

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        real_key = resolve_key(key, **kwargs)
        return bool(await self.client.exists(real_key))

    @catch_redis_errors
    async def rename(self, key: "str | BaseRedisKey", new_key: str, **kwargs: Any) -> None:
        """Rename a key (RENAME).

        Args:
            key: Redis key or a ``BaseRedisKey`` instance.
            new_key: Target key name.
            **kwargs: Extra parameters forwarded to ``resolve_key``.

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        real_key = resolve_key(key, **kwargs)
        await self.client.rename(real_key, new_key)

    @catch_redis_errors
    async def key_type(self, key: "str | BaseRedisKey", **kwargs: Any) -> str:
        """Return the data type stored at a key (TYPE).

        Args:
            key: Redis key or a ``BaseRedisKey`` instance.
            **kwargs: Extra parameters forwarded to ``resolve_key``.

        Returns:
            One of: ``"string"``, ``"list"``, ``"set"``, ``"zset"``, ``"hash"``, ``"stream"``.

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        real_key = resolve_key(key, **kwargs)
        return await self.client.type(real_key)
