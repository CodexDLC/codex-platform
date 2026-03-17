"""
codex_platform.redis_service.mixins.json_
=======================================
RedisJSON operations mixin.

Requires redis-py with JSON support (redis[hiredis] or install rejson).
All operations are async-only.

Raises RuntimeError on first use if JSON module is not available.
"""

import logging
from typing import Any

from redis.asyncio import Redis
from redis.exceptions import RedisError

log = logging.getLogger(__name__)

try:
    from redis.commands.json.path import Path as JsonPath  # noqa: F401

    _JSON_AVAILABLE = True
except ImportError as _e:
    if _e.name == "redis.commands.json":
        _JSON_AVAILABLE = False
    else:
        raise  # re-raise — что-то другое сломано


class JsonMixin:
    """
    Миксин для работы с RedisJSON.

    Доступные методы:
        json_set(key, path, obj, nx, xx) → bool (установить JSON)
        json_get(key, path) → Any (получить JSON)
        json_arrappend(key, path, *args) → int (добавить в массив)
        json_del(key, path) → int (удалить JSON)

    Требует: BaseRedisService (предоставляет self.redis_client)

    Примечание: Вызывает RuntimeError при первом использовании, если модуль redis-py JSON не доступен.
    """

    redis_client: Redis

    def _require_json(self) -> None:
        if not _JSON_AVAILABLE:
            raise RuntimeError(
                "RedisJSON module is not available. Install redis with JSON support: pip install redis[hiredis]"
            )

    async def json_set(self, key: str, path: str, obj: Any, nx: bool = False, xx: bool = False) -> bool:
        """Устанавливает значение JSON по указанному пути."""
        self._require_json()
        try:
            result = await self.redis_client.json().set(key, path, obj, nx=nx, xx=xx)
            log.debug("RedisJSON | action=set status=success key='%s' path='%s'", key, path)
            return bool(result)
        except RedisError:
            log.exception("RedisJSON | action=set status=failed reason='Redis error' key='%s'", key)
            return False

    async def json_get(self, key: str, path: str = "$") -> Any:
        """Получает значение JSON по указанному пути."""
        self._require_json()
        try:
            result = await self.redis_client.json().get(key, path)
            log.debug("RedisJSON | action=get status=found key='%s' path='%s'", key, path)
            return result
        except RedisError:
            log.exception("RedisJSON | action=get status=failed reason='Redis error' key='%s'", key)
            return None

    async def json_arrappend(self, key: str, path: str, *args: Any) -> int:
        """Добавляет элементы в массив JSON."""
        self._require_json()
        try:
            count = await self.redis_client.json().arrappend(key, path, *args)
            log.debug("RedisJSON | action=arrappend status=success key='%s' count=%s", key, count)
            return int(count) if count else 0
        except RedisError:
            log.exception("RedisJSON | action=arrappend status=failed reason='Redis error' key='%s'", key)
            return 0

    async def json_del(self, key: str, path: str = "$") -> int:
        """Удаляет значение JSON по указанному пути."""
        self._require_json()
        try:
            result = await self.redis_client.json().delete(key, path)
            log.debug("RedisJSON | action=del status=success key='%s' path='%s' count=%s", key, path, result)
            return int(result) if result else 0
        except RedisError:
            log.exception("RedisJSON | action=del status=failed reason='Redis error' key='%s'", key)
            return 0
