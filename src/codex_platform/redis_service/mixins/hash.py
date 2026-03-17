"""
codex_platform.redis_service.mixins.hash
======================================
Redis Hash operations mixin.

Requires ``redis.asyncio.Redis`` client (provided by BaseRedisService).
All operations are async-only.
"""

import json
import logging
from typing import Any

from redis.asyncio import Redis
from redis.exceptions import RedisError

from codex_platform.redis_service.keys import BaseRedisKey

log = logging.getLogger(__name__)


def _resolve_key(key: "str | BaseRedisKey", **kwargs: Any) -> str:
    """Resolve key: auto-build if BaseRedisKey, return as-is if str."""
    return key.build(**kwargs) if isinstance(key, BaseRedisKey) else key


class HashMixin:
    """
    Миксин для работы с хешами (Hash) в Redis.

    Доступные методы:
        set_hash_json(key, field, data) → None (сохранить JSON в поле)
        get_hash_json(key, field) → dict | None (получить JSON из поля)
        set_hash_field(key, field, value) → None (установить строковое поле)
        set_hash_fields(key, data) → None (установить несколько полей)
        get_hash_field(key, field) → str | None (получить значение поля)
        get_all_hash(key) → dict[str, str] | None (получить весь хеш)
        delete_hash_key(key) → None (удалить хеш целиком)

    Аргументы ``key`` принимают либо простую строку (``str``), либо экземпляр :class:`BaseRedisKey`.
    При использовании ``BaseRedisKey`` передавайте аргументы шаблона через ``**kwargs``.

    Пример::

        await service.set_hash_json(UserKey(), "profile", data, user_id=42)
        await service.set_hash_json("u:42", "profile", data)

    Требует: BaseRedisService (предоставляет self.redis_client)
    """

    redis_client: Redis

    async def set_hash_json(self, key: "str | BaseRedisKey", field: str, data: dict[str, Any], **kwargs: Any) -> None:
        """Сериализует словарь в JSON-строку и сохраняет в поле хеша Redis."""
        real_key = _resolve_key(key, **kwargs)
        try:
            data_json = json.dumps(data)
            await self.redis_client.hset(real_key, field, data_json)
            log.debug("RedisHash | action=set_json status=success key='%s' field='%s'", real_key, field)
        except TypeError:
            log.error("RedisHash | action=set_json status=failed reason='JSON serialization error' key='%s'", real_key)
        except RedisError:
            log.exception("RedisHash | action=set_json status=failed reason='Redis error' key='%s'", real_key)

    async def get_hash_json(self, key: "str | BaseRedisKey", field: str, **kwargs: Any) -> dict[str, Any] | None:
        """Получает JSON-строку из поля хеша Redis и десериализует в словарь."""
        real_key = _resolve_key(key, **kwargs)
        try:
            data_json = await self.redis_client.hget(real_key, field)
            if data_json:
                log.debug("RedisHash | action=get_json status=found key='%s' field='%s'", real_key, field)
                return json.loads(data_json)
            log.debug("RedisHash | action=get_json status=not_found key='%s' field='%s'", real_key, field)
            return None
        except json.JSONDecodeError:
            log.error(
                "RedisHash | action=get_json status=failed reason='JSON deserialization error' key='%s'", real_key
            )
            return None
        except RedisError:
            log.exception("RedisHash | action=get_json status=failed reason='Redis error' key='%s'", real_key)
            return None

    async def set_hash_field(self, key: "str | BaseRedisKey", field: str, value: str, **kwargs: Any) -> None:
        """Устанавливает значение одного поля в хеше Redis."""
        real_key = _resolve_key(key, **kwargs)
        try:
            await self.redis_client.hset(real_key, field, value)
            log.debug("RedisHash | action=set_field status=success key='%s' field='%s'", real_key, field)
        except RedisError:
            log.exception("RedisHash | action=set_field status=failed reason='Redis error' key='%s'", real_key)

    async def set_hash_fields(self, key: "str | BaseRedisKey", data: dict[str, Any], **kwargs: Any) -> None:
        """Устанавливает несколько полей в хеше Redis."""
        real_key = _resolve_key(key, **kwargs)
        try:
            await self.redis_client.hset(real_key, mapping=data)
            log.debug("RedisHash | action=set_fields status=success key='%s' fields=%s", real_key, list(data.keys()))
        except RedisError:
            log.exception("RedisHash | action=set_fields status=failed reason='Redis error' key='%s'", real_key)

    async def get_hash_field(self, key: "str | BaseRedisKey", field: str, **kwargs: Any) -> str | None:
        """Получает строковое значение одного поля из хеша Redis."""
        real_key = _resolve_key(key, **kwargs)
        try:
            value = await self.redis_client.hget(real_key, field)
            if value:
                log.debug("RedisHash | action=get_field status=found key='%s' field='%s'", real_key, field)
                return value
            log.debug("RedisHash | action=get_field status=not_found key='%s' field='%s'", real_key, field)
            return None
        except RedisError:
            log.exception("RedisHash | action=get_field status=failed reason='Redis error' key='%s'", real_key)
            return None

    async def get_all_hash(self, key: "str | BaseRedisKey", **kwargs: Any) -> dict[str, str] | None:
        """Получает все поля и значения из хеша Redis."""
        real_key = _resolve_key(key, **kwargs)
        try:
            data_dict = await self.redis_client.hgetall(real_key)
            if data_dict:
                log.debug("RedisHash | action=get_all status=found key='%s' fields_count=%d", real_key, len(data_dict))
                return data_dict
            log.debug("RedisHash | action=get_all status=not_found key='%s'", real_key)
            return None
        except RedisError:
            log.exception("RedisHash | action=get_all status=failed reason='Redis error' key='%s'", real_key)
            return None

    async def delete_hash_key(self, key: "str | BaseRedisKey", **kwargs: Any) -> None:
        """Удаляет весь хеш по ключу Redis."""
        real_key = _resolve_key(key, **kwargs)
        try:
            await self.redis_client.delete(real_key)
            log.debug("RedisHash | action=delete_key status=success key='%s'", real_key)
        except RedisError:
            log.exception("RedisHash | action=delete_key status=failed reason='Redis error' key='%s'", real_key)
