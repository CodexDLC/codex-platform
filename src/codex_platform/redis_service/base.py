"""
codex_platform.redis_service.base
==============================
Base class for Redis service.

Requires ``redis.asyncio.Redis`` client.
All operations are async-only.
"""

from redis.asyncio import Redis


class BaseRedisService:
    """Base class. Provides redis_client to all mixins via MRO."""

    def __init__(self, client: Redis) -> None:
        self.redis_client = client
