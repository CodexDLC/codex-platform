"""
codex_platform.redis_service.operations.zset
=============================================
Redis Sorted Set (ZSet) operations.

A Sorted Set is a set where every member has an associated float score.
Use it for leaderboards, priority queues, and time-based event indexes.
"""

import logging
from typing import Any

from redis.asyncio import Redis

from codex_platform.redis_service.base import catch_redis_errors
from codex_platform.redis_service.keys import BaseRedisKey, resolve_key

log = logging.getLogger(__name__)


class ZSetOperations:
    """Redis Sorted Set operations (ZADD / ZRANGE / ZRANGEBYSCORE / ZREM and more).

    Accepts an already-constructed ``redis.asyncio.Redis`` client.
    All methods wrap Redis errors in typed exceptions.

    Example::

        ops = ZSetOperations(client)
        await ops.add("leaderboard", {"alice": 1500.0, "bob": 1200.0})
        top = await ops.range("leaderboard", 0, 9, reverse=True, with_scores=True)
    """

    def __init__(self, client: Redis) -> None:
        self.client = client

    @catch_redis_errors
    async def add(self, key: "str | BaseRedisKey", mapping: dict[str, float], **kwargs: Any) -> int:
        """Add members with scores to a sorted set (ZADD).

        Args:
            key: Redis key or a ``BaseRedisKey`` instance.
            mapping: Dict of ``{member: score}`` pairs.
            **kwargs: Extra parameters forwarded to ``resolve_key``.

        Returns:
            Number of new members added (existing members with updated scores are not counted).

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        real_key = resolve_key(key, **kwargs)
        return int(await self.client.zadd(real_key, mapping))

    @catch_redis_errors
    async def score(self, key: "str | BaseRedisKey", member: str, **kwargs: Any) -> float | None:
        """Return the score of a member in a sorted set (ZSCORE).

        Args:
            key: Redis key or a ``BaseRedisKey`` instance.
            member: Member name.
            **kwargs: Extra parameters forwarded to ``resolve_key``.

        Returns:
            Float score of the member, or ``None`` if the member does not exist.

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        real_key = resolve_key(key, **kwargs)
        val = await self.client.zscore(real_key, member)
        return float(val) if val is not None else None

    @catch_redis_errors
    async def rank(self, key: "str | BaseRedisKey", member: str, reverse: bool = False, **kwargs: Any) -> int | None:
        """Return the rank (position) of a member in a sorted set (ZRANK / ZREVRANK).

        Args:
            key: Redis key or a ``BaseRedisKey`` instance.
            member: Member name.
            reverse: If ``True``, use ZREVRANK (rank by descending score). Defaults to ``False``.
            **kwargs: Extra parameters forwarded to ``resolve_key``.

        Returns:
            Zero-based rank of the member, or ``None`` if the member does not exist.

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        real_key = resolve_key(key, **kwargs)
        fn = self.client.zrevrank if reverse else self.client.zrank
        result = await fn(real_key, member)
        return int(result) if result is not None else None

    @catch_redis_errors
    async def range(
        self,
        key: "str | BaseRedisKey",
        start: int = 0,
        end: int = -1,
        reverse: bool = False,
        with_scores: bool = False,
        **kwargs: Any,
    ) -> list[str] | list[tuple[str, float]]:
        """Return a range of members by rank (ZRANGE / ZREVRANGE).

        Args:
            key: Redis key or a ``BaseRedisKey`` instance.
            start: Start rank (0-based).
            end: End rank inclusive. ``-1`` means the last member.
            reverse: If ``True``, return members in descending score order (ZREVRANGE).
            with_scores: If ``True``, return ``[(member, score), ...]`` tuples.
            **kwargs: Extra parameters forwarded to ``resolve_key``.

        Returns:
            List of member strings, or list of ``(member, score)`` tuples if ``with_scores=True``.

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        real_key = resolve_key(key, **kwargs)
        if reverse:
            result = await self.client.zrevrange(real_key, start, end, withscores=with_scores)
        else:
            result = await self.client.zrange(real_key, start, end, withscores=with_scores)
        return result

    @catch_redis_errors
    async def range_by_score(
        self,
        key: "str | BaseRedisKey",
        min_score: float,
        max_score: float,
        with_scores: bool = False,
        **kwargs: Any,
    ) -> list[str] | list[tuple[str, float]]:
        """Return members within a score range (ZRANGEBYSCORE).

        Args:
            key: Redis key or a ``BaseRedisKey`` instance.
            min_score: Minimum score (inclusive).
            max_score: Maximum score (inclusive).
            with_scores: If ``True``, return ``[(member, score), ...]`` tuples.
            **kwargs: Extra parameters forwarded to ``resolve_key``.

        Returns:
            List of member strings, or list of ``(member, score)`` tuples if ``with_scores=True``.

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        real_key = resolve_key(key, **kwargs)
        return await self.client.zrangebyscore(real_key, min_score, max_score, withscores=with_scores)

    @catch_redis_errors
    async def remove(self, key: "str | BaseRedisKey", *members: str, **kwargs: Any) -> int:
        """Remove one or more members from a sorted set (ZREM).

        Args:
            key: Redis key or a ``BaseRedisKey`` instance.
            *members: Member names to remove.
            **kwargs: Extra parameters forwarded to ``resolve_key``.

        Returns:
            Number of members actually removed.

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        real_key = resolve_key(key, **kwargs)
        return int(await self.client.zrem(real_key, *members))

    @catch_redis_errors
    async def card(self, key: "str | BaseRedisKey", **kwargs: Any) -> int:
        """Return the number of members in a sorted set (ZCARD).

        Args:
            key: Redis key or a ``BaseRedisKey`` instance.
            **kwargs: Extra parameters forwarded to ``resolve_key``.

        Returns:
            Number of members. ``0`` if the key does not exist.

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        real_key = resolve_key(key, **kwargs)
        return int(await self.client.zcard(real_key))

    @catch_redis_errors
    async def increment(self, key: "str | BaseRedisKey", member: str, amount: float = 1.0, **kwargs: Any) -> float:
        """Increment the score of a member by the given amount (ZINCRBY).

        Args:
            key: Redis key or a ``BaseRedisKey`` instance.
            member: Member name.
            amount: Increment value. Defaults to ``1.0``.
            **kwargs: Extra parameters forwarded to ``resolve_key``.

        Returns:
            New score of the member after incrementing.

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        real_key = resolve_key(key, **kwargs)
        return float(await self.client.zincrby(real_key, amount, member))

    @catch_redis_errors
    async def count(self, key: "str | BaseRedisKey", min_score: float, max_score: float, **kwargs: Any) -> int:
        """Count members within a score range (ZCOUNT).

        Args:
            key: Redis key or a ``BaseRedisKey`` instance.
            min_score: Minimum score (inclusive).
            max_score: Maximum score (inclusive).
            **kwargs: Extra parameters forwarded to ``resolve_key``.

        Returns:
            Number of members with score in ``[min_score, max_score]``.

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        real_key = resolve_key(key, **kwargs)
        return int(await self.client.zcount(real_key, min_score, max_score))

    @catch_redis_errors
    async def remove_by_rank(self, key: "str | BaseRedisKey", start: int, end: int, **kwargs: Any) -> int:
        """Remove members by rank range (ZREMRANGEBYRANK).

        Args:
            key: Redis key or a ``BaseRedisKey`` instance.
            start: Start rank (inclusive, 0-based).
            end: End rank (inclusive).
            **kwargs: Extra parameters forwarded to ``resolve_key``.

        Returns:
            Number of members removed.

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        real_key = resolve_key(key, **kwargs)
        return int(await self.client.zremrangebyrank(real_key, start, end))

    @catch_redis_errors
    async def remove_by_score(
        self, key: "str | BaseRedisKey", min_score: float, max_score: float, **kwargs: Any
    ) -> int:
        """Remove members within a score range (ZREMRANGEBYSCORE).

        Args:
            key: Redis key or a ``BaseRedisKey`` instance.
            min_score: Minimum score (inclusive).
            max_score: Maximum score (inclusive).
            **kwargs: Extra parameters forwarded to ``resolve_key``.

        Returns:
            Number of members removed.

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        real_key = resolve_key(key, **kwargs)
        return int(await self.client.zremrangebyscore(real_key, min_score, max_score))
