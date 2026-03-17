"""
codex_platform.redis_service.operations.hash
=============================================
Redis Hash operations.
"""

import json
import logging
from typing import Any

from redis.asyncio import Redis

from codex_platform.redis_service.base import catch_redis_errors
from codex_platform.redis_service.exceptions import RedisDataError
from codex_platform.redis_service.keys import BaseRedisKey, resolve_key

log = logging.getLogger(__name__)


class HashOperations:
    """Redis Hash operations (HSET / HGET / HGETALL / HDEL and more).

    Accepts an already-constructed ``redis.asyncio.Redis`` client.
    All methods wrap Redis errors in typed exceptions.

    Example::

        ops = HashOperations(client)
        await ops.set_json("user:42", "profile", {"name": "Alice"})
        profile = await ops.get_json("user:42", "profile")
    """

    def __init__(self, client: Redis) -> None:
        self.client = client

    @catch_redis_errors
    async def set_json(self, key: "str | BaseRedisKey", field: str, data: dict[str, Any], **kwargs: Any) -> None:
        """Serialize a dict to JSON and store it in a hash field (HSET).

        Args:
            key: Redis key or a ``BaseRedisKey`` instance.
            field: Hash field name.
            data: Dictionary to serialize as JSON.
            **kwargs: Extra parameters forwarded to ``resolve_key`` (e.g. ``user_id=42``).

        Raises:
            RedisDataError: If ``data`` cannot be serialized to JSON.
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        real_key = resolve_key(key, **kwargs)
        try:
            data_json = json.dumps(data)
        except TypeError as e:
            raise RedisDataError(f"JSON serialization error for key='{real_key}': {e}") from e
        await self.client.hset(real_key, field, data_json)

    @catch_redis_errors
    async def get_json(self, key: "str | BaseRedisKey", field: str, **kwargs: Any) -> dict[str, Any] | None:
        """Retrieve a hash field and deserialize it from JSON (HGET).

        Args:
            key: Redis key or a ``BaseRedisKey`` instance.
            field: Hash field name.
            **kwargs: Extra parameters forwarded to ``resolve_key``.

        Returns:
            Deserialized dictionary, or ``None`` if the field does not exist.

        Raises:
            RedisDataError: If the field value is not valid JSON.
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        real_key = resolve_key(key, **kwargs)
        raw = await self.client.hget(real_key, field)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            raise RedisDataError(f"Invalid JSON in key='{real_key}' field='{field}': {e}") from e

    @catch_redis_errors
    async def set_field(self, key: "str | BaseRedisKey", field: str, value: str, **kwargs: Any) -> None:
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
        await self.client.hset(real_key, field, value)

    @catch_redis_errors
    async def set_fields(self, key: "str | BaseRedisKey", data: dict[str, Any], **kwargs: Any) -> None:
        """Set multiple hash fields in a single call (HSET mapping).

        Args:
            key: Redis key or a ``BaseRedisKey`` instance.
            data: Mapping of ``{field: value}`` pairs to write.
            **kwargs: Extra parameters forwarded to ``resolve_key``.

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        real_key = resolve_key(key, **kwargs)
        await self.client.hset(real_key, mapping=data)

    @catch_redis_errors
    async def get_field(self, key: "str | BaseRedisKey", field: str, **kwargs: Any) -> str | None:
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
        value = await self.client.hget(real_key, field)
        return str(value) if value is not None else None

    @catch_redis_errors
    async def get_fields(self, key: "str | BaseRedisKey", *fields: str, **kwargs: Any) -> list[str | None]:
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
        values = await self.client.hmget(real_key, list(fields))
        return [str(v) if v is not None else None for v in values]

    @catch_redis_errors
    async def get_all(self, key: "str | BaseRedisKey", **kwargs: Any) -> dict[str, str] | None:
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
        data = await self.client.hgetall(real_key)
        return data if data else None

    @catch_redis_errors
    async def delete_field(self, key: "str | BaseRedisKey", *fields: str, **kwargs: Any) -> int:
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
        return int(await self.client.hdel(real_key, *fields))

    @catch_redis_errors
    async def delete(self, key: "str | BaseRedisKey", **kwargs: Any) -> None:
        """Delete the entire hash key (DEL).

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
    async def exists_field(self, key: "str | BaseRedisKey", field: str, **kwargs: Any) -> bool:
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
        return bool(await self.client.hexists(real_key, field))

    @catch_redis_errors
    async def keys(self, key: "str | BaseRedisKey", **kwargs: Any) -> list[str]:
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
        return await self.client.hkeys(real_key)

    @catch_redis_errors
    async def values(self, key: "str | BaseRedisKey", **kwargs: Any) -> list[str]:
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
        return await self.client.hvals(real_key)

    @catch_redis_errors
    async def length(self, key: "str | BaseRedisKey", **kwargs: Any) -> int:
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
        return int(await self.client.hlen(real_key))

    @catch_redis_errors
    async def increment(self, key: "str | BaseRedisKey", field: str, amount: int = 1, **kwargs: Any) -> int:
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
        return int(await self.client.hincrby(real_key, field, amount))
