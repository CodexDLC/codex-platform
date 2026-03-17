"""
codex_platform.redis_service.managers.base_manager
====================================================
Base class for Redis business-logic managers.
"""

from redis.asyncio import Redis

from codex_platform.redis_service.operations import HashOperations, StringOperations


class BaseRedisManager:
    """Base manager that initialises common Redis operation helpers.

    Subclass and add only the operation attributes your manager actually needs.

    Example::

        class SiteSettingsManager(BaseRedisManager):
            async def get_settings(self) -> dict:
                return await self.hash.get_all("site:settings") or {}
    """

    def __init__(self, redis_client: Redis) -> None:
        """Initialize the manager with an existing async Redis client.

        Args:
            redis_client: An already-constructed ``redis.asyncio.Redis`` instance.
        """
        self.hash = HashOperations(redis_client)
        self.string = StringOperations(redis_client)
