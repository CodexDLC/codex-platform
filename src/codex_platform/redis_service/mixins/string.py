"""
codex_platform.redis_service.mixins.string
========================================
Redis String/Key operations mixin.

Requires ``redis.asyncio.Redis`` client (provided by BaseRedisService).
All operations are async-only.
"""

import logging

from redis.asyncio import Redis
from redis.exceptions import RedisError

log = logging.getLogger(__name__)


class StringMixin:
    """
    Миксин для работы со строками (String) и ключами в Redis.

    Доступные методы:
        set_value(key, value, ttl) → None (установить значение)
        get_value(key) → str | None (получить значение)
        delete_key(key) → None (удалить ключ)
        delete_by_pattern(pattern) → int (удалить по паттерну)
        expire(key, time) → bool (установить TTL)
        key_exists(key) → bool (проверить существование)

    Требует: BaseRedisService (предоставляет self.redis_client)
    """

    redis_client: Redis

    async def set_value(self, key: str, value: str, ttl: int | None = None) -> None:
        """Устанавливает строковое значение для ключа Redis."""
        try:
            await self.redis_client.set(key, value, ex=ttl)
            log.debug("RedisString | action=set status=success key='%s' ttl=%s", key, ttl)
        except RedisError:
            log.exception("RedisString | action=set status=failed reason='Redis error' key='%s'", key)

    async def get_value(self, key: str) -> str | None:
        """Получает строковое значение по ключу Redis."""
        try:
            val = await self.redis_client.get(key)
            if val is not None:
                log.debug("RedisString | action=get status=found key='%s'", key)
                return str(val)
            log.debug("RedisString | action=get status=not_found key='%s'", key)
            return None
        except RedisError:
            log.exception("RedisString | action=get status=failed reason='Redis error' key='%s'", key)
            return None

    async def delete_key(self, key: str) -> None:
        """Удаляет ключ любого типа из Redis."""
        try:
            await self.redis_client.delete(key)
            log.debug("RedisKey | action=delete status=success key='%s'", key)
        except RedisError:
            log.exception("RedisKey | action=delete status=failed reason='Redis error' key='%s'", key)

    async def delete_by_pattern(self, pattern: str) -> int:
        """Удаляет ключи из Redis, соответствующие паттерну (scan_iter)."""
        try:
            keys_to_delete = [k async for k in self.redis_client.scan_iter(match=pattern)]
            deleted_count = 0
            if keys_to_delete:
                deleted_count = await self.redis_client.delete(*keys_to_delete)
            log.debug(
                "RedisKey | action=delete_by_pattern status=success pattern='%s' deleted=%s", pattern, deleted_count
            )
            return int(deleted_count)
        except RedisError:
            log.exception(
                "RedisKey | action=delete_by_pattern status=failed reason='Redis error' pattern='%s'", pattern
            )
            return 0

    async def expire(self, key: str, time: int) -> bool:
        """Устанавливает время жизни (TTL) для ключа."""
        try:
            result = await self.redis_client.expire(key, time)
            log.debug("RedisKey | action=expire status=success key='%s' ttl=%d", key, time)
            return bool(result)
        except RedisError:
            log.exception("RedisKey | action=expire status=failed reason='Redis error' key='%s'", key)
            return False

    async def key_exists(self, key: str) -> bool:
        """Проверяет существование ключа в Redis."""
        try:
            exists = await self.redis_client.exists(key)
            log.debug("RedisKey | action=exists status=checked key='%s' result=%s", key, bool(exists))
            return bool(exists)
        except RedisError:
            log.exception("RedisKey | action=exists status=failed reason='Redis error' key='%s'", key)
            return False
