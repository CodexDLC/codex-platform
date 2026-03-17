"""
codex_platform.redis_service.operations.set_
=============================================
Redis Set operations.
"""

import logging
from typing import Any

from redis.asyncio import Redis

from codex_platform.redis_service.base import catch_redis_errors
from codex_platform.redis_service.keys import BaseRedisKey, resolve_key

log = logging.getLogger(__name__)


class SetOperations:
    """Redis Set operations (SADD / SREM / SMEMBERS / SISMEMBER and more).

    Accepts an already-constructed ``redis.asyncio.Redis`` client.
    All methods wrap Redis errors in typed exceptions.

    Example::

        ops = SetOperations(client)
        await ops.add("tags:post:42", "python", "redis")
        has_tag = await ops.is_member("tags:post:42", "python")
    """

    def __init__(self, client: Redis) -> None:
        self.client = client

    @catch_redis_errors
    async def add(self, key: "str | BaseRedisKey", *values: str | int, **kwargs: Any) -> int:
        """Add one or more members to a set (SADD).

        Args:
            key: Redis key or a ``BaseRedisKey`` instance.
            *values: Values to add. Integers are coerced to strings.
            **kwargs: Extra parameters forwarded to ``resolve_key``.

        Returns:
            Number of members actually added (already-existing members are not counted).

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        real_key = resolve_key(key, **kwargs)
        return int(await self.client.sadd(real_key, *[str(v) for v in values]))

    @catch_redis_errors
    async def remove(self, key: "str | BaseRedisKey", *values: str | int, **kwargs: Any) -> int:
        """Remove one or more members from a set (SREM).

        Args:
            key: Redis key or a ``BaseRedisKey`` instance.
            *values: Values to remove. Integers are coerced to strings.
            **kwargs: Extra parameters forwarded to ``resolve_key``.

        Returns:
            Number of members actually removed.

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        real_key = resolve_key(key, **kwargs)
        return int(await self.client.srem(real_key, *[str(v) for v in values]))

    @catch_redis_errors
    async def members(self, key: "str | BaseRedisKey", **kwargs: Any) -> set[str]:
        """Return all members of a set (SMEMBERS).

        Args:
            key: Redis key or a ``BaseRedisKey`` instance.
            **kwargs: Extra parameters forwarded to ``resolve_key``.

        Returns:
            Set of all member strings. Empty set if the key does not exist.

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        real_key = resolve_key(key, **kwargs)
        return await self.client.smembers(real_key)

    @catch_redis_errors
    async def is_member(self, key: "str | BaseRedisKey", value: str | int, **kwargs: Any) -> bool:
        """Check whether a value is a member of a set (SISMEMBER).

        Args:
            key: Redis key or a ``BaseRedisKey`` instance.
            value: Value to check. Integers are coerced to strings.
            **kwargs: Extra parameters forwarded to ``resolve_key``.

        Returns:
            ``True`` if the value is in the set, ``False`` otherwise.

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        real_key = resolve_key(key, **kwargs)
        return bool(await self.client.sismember(real_key, str(value)))

    @catch_redis_errors
    async def card(self, key: "str | BaseRedisKey", **kwargs: Any) -> int:
        """Return the number of members in a set (SCARD).

        Args:
            key: Redis key or a ``BaseRedisKey`` instance.
            **kwargs: Extra parameters forwarded to ``resolve_key``.

        Returns:
            Set cardinality. ``0`` if the key does not exist.

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        real_key = resolve_key(key, **kwargs)
        return int(await self.client.scard(real_key))

    @catch_redis_errors
    async def pop(self, key: "str | BaseRedisKey", count: int = 1, **kwargs: Any) -> set[str]:
        """Remove and return random members from a set (SPOP).

        Args:
            key: Redis key or a ``BaseRedisKey`` instance.
            count: Number of members to pop. Defaults to ``1``.
            **kwargs: Extra parameters forwarded to ``resolve_key``.

        Returns:
            Set of popped members. Empty set if the key does not exist.

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        real_key = resolve_key(key, **kwargs)
        result = await self.client.spop(real_key, count)
        return set(result) if result else set()

    @catch_redis_errors
    async def random(self, key: "str | BaseRedisKey", count: int = 1, **kwargs: Any) -> list[str]:
        """Return random members without removing them (SRANDMEMBER).

        Args:
            key: Redis key or a ``BaseRedisKey`` instance.
            count: Number of random members to return.
            **kwargs: Extra parameters forwarded to ``resolve_key``.

        Returns:
            List of random members (may contain duplicates if ``count > cardinality``).

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        real_key = resolve_key(key, **kwargs)
        return await self.client.srandmember(real_key, count)

    @catch_redis_errors
    async def union(self, *keys: str) -> set[str]:
        """Return the union of multiple sets (SUNION).

        Args:
            *keys: Redis key strings.

        Returns:
            Set containing all members from all given sets.

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        return await self.client.sunion(list(keys))

    @catch_redis_errors
    async def inter(self, *keys: str) -> set[str]:
        """Return the intersection of multiple sets (SINTER).

        Args:
            *keys: Redis key strings.

        Returns:
            Set containing only members present in all given sets.

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        return await self.client.sinter(list(keys))

    @catch_redis_errors
    async def diff(self, *keys: str) -> set[str]:
        """Return the difference between the first set and all subsequent sets (SDIFF).

        Args:
            *keys: Redis key strings. The first key is the base set.

        Returns:
            Set of members present in the first set but not in any of the others.

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        return await self.client.sdiff(list(keys))
