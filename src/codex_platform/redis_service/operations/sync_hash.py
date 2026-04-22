"""
codex_platform.redis_service.operations.sync_hash
=================================================
Redis Hash synchronous operations.
"""

import logging
from collections.abc import Callable
from typing import Any

from redis import Redis

from codex_platform.redis_service.base import catch_redis_errors_sync
from codex_platform.redis_service.keys import BaseRedisKey, resolve_key

log = logging.getLogger(__name__)


class SyncHashOperations:
    """Redis Hash synchronous operations (HSET / HGET / HGETALL / HDEL and more).

    Accepts an already-constructed ``redis.Redis`` client.
    All methods wrap Redis errors in typed exceptions.

    Example::

        ops = SyncHashOperations(client)
        ops.set_fields("user:42", {"name": "Alice"})
        name = ops.get_field("user:42", "name")
    """

    def __init__(self, client: Redis) -> None:
        self.client = client

    @catch_redis_errors_sync
    def get_field(self, key: "str | BaseRedisKey", field: str, **kwargs: Any) -> str | None:
        """Retrieve a single hash field as a string (HGET).

        Args:
            key: Redis key or a ``BaseRedisKey`` instance.
            field: Hash field name.
            **kwargs: Extra parameters forwarded to ``resolve_key``.

        Returns:
            String value of the field, or ``None`` if it does not exist.

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        real_key = resolve_key(key, **kwargs)
        value = self.client.hget(real_key, field)
        return str(value) if value is not None else None

    @catch_redis_errors_sync
    def set_field(self, key: "str | BaseRedisKey", field: str, value: str, **kwargs: Any) -> None:
        """Set a single string field in a hash (HSET).

        Args:
            key: Redis key or a ``BaseRedisKey`` instance.
            field: Hash field name.
            value: String value to store.
            **kwargs: Extra parameters forwarded to ``resolve_key``.

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        real_key = resolve_key(key, **kwargs)
        self.client.hset(real_key, field, value)

    @catch_redis_errors_sync
    def delete_field(self, key: "str | BaseRedisKey", *fields: str, **kwargs: Any) -> int:
        """Delete one or more fields from a hash (HDEL).

        Args:
            key: Redis key or a ``BaseRedisKey`` instance.
            *fields: Field names to delete.
            **kwargs: Extra parameters forwarded to ``resolve_key``.

        Returns:
            Number of fields actually deleted.

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        real_key = resolve_key(key, **kwargs)
        return int(self.client.hdel(real_key, *fields))

    @catch_redis_errors_sync
    def get_all(self, key: "str | BaseRedisKey", **kwargs: Any) -> dict[str, str] | None:
        """Retrieve all fields and values from a hash (HGETALL).

        Args:
            key: Redis key or a ``BaseRedisKey`` instance.
            **kwargs: Extra parameters forwarded to ``resolve_key``.

        Returns:
            Dict of ``{field: value}``, or ``None`` if the hash does not exist.

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        real_key = resolve_key(key, **kwargs)
        data = self.client.hgetall(real_key)
        return data if data else None

    @catch_redis_errors_sync
    def get_fields(self, key: "str | BaseRedisKey", *fields: str, **kwargs: Any) -> list[str | None]:
        """Retrieve multiple hash fields in a single request (HMGET).

        Args:
            key: Redis key or a ``BaseRedisKey`` instance.
            *fields: Field names to retrieve.
            **kwargs: Extra parameters forwarded to ``resolve_key``.

        Returns:
            List of values in the same order as ``fields``.
            ``None`` for fields that do not exist.

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        real_key = resolve_key(key, **kwargs)
        values = self.client.hmget(real_key, list(fields))
        return [str(v) if v is not None else None for v in values]

    @catch_redis_errors_sync
    def delete(self, key: "str | BaseRedisKey", **kwargs: Any) -> None:
        """Delete the entire hash key (DEL).

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
    def exists_field(self, key: "str | BaseRedisKey", field: str, **kwargs: Any) -> bool:
        """Check whether a field exists in a hash (HEXISTS).

        Args:
            key: Redis key or a ``BaseRedisKey`` instance.
            field: Hash field name to check.
            **kwargs: Extra parameters forwarded to ``resolve_key``.

        Returns:
            ``True`` if the field exists, ``False`` otherwise.

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        real_key = resolve_key(key, **kwargs)
        return bool(self.client.hexists(real_key, field))

    @catch_redis_errors_sync
    def keys(self, key: "str | BaseRedisKey", **kwargs: Any) -> list[str]:
        """Return all field names of a hash (HKEYS).

        Args:
            key: Redis key or a ``BaseRedisKey`` instance.
            **kwargs: Extra parameters forwarded to ``resolve_key``.

        Returns:
            List of field names. Empty list if the hash does not exist.

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        real_key = resolve_key(key, **kwargs)
        return list(self.client.hkeys(real_key))

    @catch_redis_errors_sync
    def values(self, key: "str | BaseRedisKey", **kwargs: Any) -> list[str]:
        """Return all field values of a hash (HVALS).

        Args:
            key: Redis key or a ``BaseRedisKey`` instance.
            **kwargs: Extra parameters forwarded to ``resolve_key``.

        Returns:
            List of field values. Empty list if the hash does not exist.

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        real_key = resolve_key(key, **kwargs)
        return list(self.client.hvals(real_key))

    @catch_redis_errors_sync
    def length(self, key: "str | BaseRedisKey", **kwargs: Any) -> int:
        """Return the number of fields in a hash (HLEN).

        Args:
            key: Redis key or a ``BaseRedisKey`` instance.
            **kwargs: Extra parameters forwarded to ``resolve_key``.

        Returns:
            Number of fields. ``0`` if the hash does not exist.

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        real_key = resolve_key(key, **kwargs)
        return int(self.client.hlen(real_key))

    @catch_redis_errors_sync
    def increment(self, key: "str | BaseRedisKey", field: str, amount: int = 1, **kwargs: Any) -> int:
        """Increment a numeric hash field by the given amount (HINCRBY).

        Args:
            key: Redis key or a ``BaseRedisKey`` instance.
            field: Numeric field name.
            amount: Increment step. Defaults to ``1``.
            **kwargs: Extra parameters forwarded to ``resolve_key``.

        Returns:
            New value of the field after incrementing.

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        real_key = resolve_key(key, **kwargs)
        return int(self.client.hincrby(real_key, field, amount))

    @catch_redis_errors_sync
    def set_fields(
        self,
        key: "str | BaseRedisKey",
        data: dict[str, Any],
        *,
        encoder: Callable[[Any], Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Set multiple hash fields in a single call (HSET mapping).

        Args:
            key: Redis key or a ``BaseRedisKey`` instance.
            data: Mapping of ``{field: value}`` pairs to write.
            encoder: Optional callable to transform values before setting.
            **kwargs: Extra parameters forwarded to ``resolve_key``.

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        real_key = resolve_key(key, **kwargs)
        if encoder:
            data = {k: encoder(v) for k, v in data.items()}
        self.client.hset(real_key, mapping=data)
