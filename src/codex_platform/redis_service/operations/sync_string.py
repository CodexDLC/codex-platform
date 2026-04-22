"""
codex_platform.redis_service.operations.sync_string
===================================================
Redis String/Key synchronous operations.
"""

import logging
from typing import Any

from redis import Redis

from codex_platform.redis_service.base import catch_redis_errors_sync
from codex_platform.redis_service.keys import BaseRedisKey, resolve_key

log = logging.getLogger(__name__)


class SyncStringOperations:
    """Redis String and key-level synchronous operations (SET / GET / EXPIRE / TTL and more).

    Accepts an already-constructed ``redis.Redis`` client.
    All methods wrap Redis errors in typed exceptions.

    Example::

        ops = SyncStringOperations(client)
        ops.set("session:abc", "token-value", ttl=3600)
        token = ops.get("session:abc")
    """

    def __init__(self, client: Redis) -> None:
        self.client = client

    @catch_redis_errors_sync
    def set(self, key: "str | BaseRedisKey", value: str, ttl: int | None = None, **kwargs: Any) -> None:
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
        self.client.set(real_key, value, ex=ttl)

    @catch_redis_errors_sync
    def get(self, key: "str | BaseRedisKey", **kwargs: Any) -> str | None:
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
        val = self.client.get(real_key)
        return str(val) if val is not None else None

    @catch_redis_errors_sync
    def mget(self, *keys: str) -> list[str | None]:
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
        values = self.client.mget(list(keys))
        return [str(v) if v is not None else None for v in values]

    @catch_redis_errors_sync
    def mset(self, mapping: dict[str, str]) -> None:
        """Set values for multiple keys in a single call (MSET).

        Args:
            mapping: Dict of ``{key: value}`` pairs to write.

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        self.client.mset(mapping)

    @catch_redis_errors_sync
    def incr(self, key: "str | BaseRedisKey", **kwargs: Any) -> int:
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
        return int(self.client.incr(real_key))

    @catch_redis_errors_sync
    def delete(self, key: "str | BaseRedisKey", **kwargs: Any) -> None:
        """Delete a key (DEL).

        Args:
            key: Redis key or a ``BaseRedisKey`` instance.
            **kwargs: Extra parameters forwarded to ``resolve_key``.

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        real_key = resolve_key(key, **kwargs)
        self.client.delete(real_key)

    @catch_redis_errors_sync
    def expire(self, key: "str | BaseRedisKey", ttl: int, **kwargs: Any) -> bool:
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
        return bool(self.client.expire(real_key, ttl))

    @catch_redis_errors_sync
    def ttl(self, key: "str | BaseRedisKey", **kwargs: Any) -> int:
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
        return int(self.client.ttl(real_key))

    @catch_redis_errors_sync
    def exists(self, key: "str | BaseRedisKey", **kwargs: Any) -> bool:
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
        return bool(self.client.exists(real_key))
