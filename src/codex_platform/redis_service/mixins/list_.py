"""
codex_platform.redis_service.mixins.list_
=======================================
Redis List operations mixin.

Requires ``redis.asyncio.Redis`` client (provided by BaseRedisService).
All operations are async-only.
"""

import logging

from redis.asyncio import Redis
from redis.exceptions import RedisError

log = logging.getLogger(__name__)


class ListMixin:
    """
    Миксин для работы со списками (List) в Redis.

    Доступные методы:
        push_to_list(key, value) → None (добавить в конец)
        pop_from_list_left(key) → str | None (извлечь с начала)
        get_list_range(key, start, end) → list[str] (получить диапазон)
        get_list_length(key) → int (получить длину)

    Требует: BaseRedisService (предоставляет self.redis_client)
    """

    redis_client: Redis

    async def push_to_list(self, key: str, value: str) -> None:
        """Добавляет элемент в конец списка Redis (RPUSH)."""
        try:
            await self.redis_client.rpush(key, value)
            log.debug("RedisList | action=push status=success key='%s'", key)
        except RedisError:
            log.exception("RedisList | action=push status=failed reason='Redis error' key='%s'", key)

    async def pop_from_list_left(self, key: str) -> str | None:
        """Удаляет и возвращает первый элемент списка Redis (LPOP)."""
        try:
            value = await self.redis_client.lpop(key)
            if value:
                log.debug("RedisList | action=lpop status=success key='%s'", key)
                return str(value)
            return None
        except RedisError:
            log.exception("RedisList | action=lpop status=failed reason='Redis error' key='%s'", key)
            return None

    async def get_list_range(self, key: str, start: int = 0, end: int = -1) -> list[str]:
        """Возвращает диапазон элементов из списка Redis."""
        try:
            result = await self.redis_client.lrange(key, start, end)
            log.debug("RedisList | action=get_range status=success key='%s' count=%d", key, len(result))
            return result
        except RedisError:
            log.exception("RedisList | action=get_range status=failed reason='Redis error' key='%s'", key)
            return []

    async def get_list_length(self, key: str) -> int:
        """Возвращает длину списка Redis."""
        try:
            count = await self.redis_client.llen(key)
            log.debug("RedisList | action=len status=success key='%s' count=%s", key, count)
            return int(count) if count else 0
        except RedisError:
            log.exception("RedisList | action=len status=failed reason='Redis error' key='%s'", key)
            return 0
