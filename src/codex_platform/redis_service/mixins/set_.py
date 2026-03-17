"""
codex_platform.redis_service.mixins.set_
======================================
Redis Set operations mixin.

Requires ``redis.asyncio.Redis`` client (provided by BaseRedisService).
All operations are async-only.
"""

import logging

from redis.asyncio import Redis
from redis.exceptions import RedisError

log = logging.getLogger(__name__)


class SetMixin:
    """
    Миксин для работы с множествами (Set) в Redis.

    Доступные методы:
        add_to_set(key, value) → None (добавить в множество)
        get_set_members(key) → set[str] (получить все элементы)
        is_set_member(key, value) → bool (проверить наличие)
        remove_from_set(key, value) → None (удалить из множества)

    Требует: BaseRedisService (предоставляет self.redis_client)
    """

    redis_client: Redis

    async def add_to_set(self, key: str, value: str | int) -> None:
        """Добавляет значение в множество Redis."""
        try:
            await self.redis_client.sadd(key, str(value))
            log.debug("RedisSet | action=add status=success key='%s' value='%s'", key, value)
        except RedisError:
            log.exception("RedisSet | action=add status=failed reason='Redis error' key='%s'", key)

    async def get_set_members(self, key: str) -> set[str]:
        """Возвращает все элементы множества Redis."""
        try:
            members = await self.redis_client.smembers(key)
            log.debug("RedisSet | action=get_all status=success key='%s' members_count=%d", key, len(members))
            return members
        except RedisError:
            log.exception("RedisSet | action=get_all status=failed reason='Redis error' key='%s'", key)
            return set()

    async def is_set_member(self, key: str, value: str | int) -> bool:
        """Проверяет, является ли значение элементом множества Redis."""
        try:
            is_member = await self.redis_client.sismember(key, str(value))
            log.debug(
                "RedisSet | action=is_member status=checked key='%s' value='%s' result=%s", key, value, bool(is_member)
            )
            return bool(is_member)
        except RedisError:
            log.exception("RedisSet | action=is_member status=failed reason='Redis error' key='%s'", key)
            return False

    async def remove_from_set(self, key: str, value: str | int) -> None:
        """Удаляет значение из множества Redis."""
        try:
            await self.redis_client.srem(key, str(value))
            log.debug("RedisSet | action=remove status=success key='%s' value='%s'", key, value)
        except RedisError:
            log.exception("RedisSet | action=remove status=failed reason='Redis error' key='%s'", key)
