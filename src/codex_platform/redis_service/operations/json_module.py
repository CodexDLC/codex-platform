"""
codex_platform.redis_service.operations.json_module
====================================================
RedisJSON module operations (JSON.SET / JSON.GET / ...).

Requires the RedisJSON server module to be loaded on the Redis instance.
Raises ``RuntimeError`` on first use if the module is not available in redis-py.
"""

import logging
from typing import Any

from redis.asyncio import Redis

from codex_platform.redis_service.base import catch_redis_errors

log = logging.getLogger(__name__)

try:
    from redis.commands.json.path import Path as JsonPath  # noqa: F401
    _JSON_AVAILABLE = True
except ImportError:
    _JSON_AVAILABLE = False


class JsonModuleOperations:
    """Redis JSON operations using the server-side RedisJSON module (JSON.* commands).

    Requires the RedisJSON module on the server and redis-py with JSON support.
    Supports path-based access, atomic updates, array append, and more.

    Example::

        svc = JsonModuleOperations(client)
        await svc.set("user:42", "$", {"name": "Alice", "age": 30})
        name = await svc.get("user:42", "$.name")  # [["Alice"]]
    """

    def __init__(self, client: Redis) -> None:
        self.client = client

    def _require_json(self) -> None:
        if not _JSON_AVAILABLE:
            raise RuntimeError(
                "RedisJSON module not available in redis-py. "
                "Install: pip install redis[hiredis]"
            )

    @catch_redis_errors
    async def set(self, key: str, path: str, obj: Any, nx: bool = False, xx: bool = False) -> bool:
        """Set a JSON value at the given path (JSON.SET).

        Args:
            key: Redis key string.
            path: JSONPath expression, e.g. ``$`` or ``$.field``.
            obj: Any JSON-serializable object.
            nx: Set only if the key does not exist.
            xx: Set only if the key already exists.

        Returns:
            ``True`` if the value was successfully set.

        Raises:
            RuntimeError: If the RedisJSON module is not available.
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        self._require_json()
        result = await self.client.json().set(key, path, obj, nx=nx, xx=xx)  # type: ignore[no-untyped-call]
        log.debug("JsonModuleOps | set key='%s' path='%s'", key, path)
        return bool(result)

    @catch_redis_errors
    async def get(self, key: str, path: str = "$") -> Any:
        """Retrieve a JSON value at the given path (JSON.GET).

        Args:
            key: Redis key string.
            path: JSONPath expression. Defaults to ``$`` (the whole document).

        Returns:
            Parsed value, or ``None`` if the key does not exist.

        Raises:
            RuntimeError: If the RedisJSON module is not available.
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        self._require_json()
        return await self.client.json().get(key, path)  # type: ignore[no-untyped-call]

    @catch_redis_errors
    async def arrappend(self, key: str, path: str, *args: Any) -> int:
        """Append elements to a JSON array at the given path (JSON.ARRAPPEND).

        Args:
            key: Redis key string.
            path: JSONPath expression pointing to an array.
            *args: Values to append to the array.

        Returns:
            New length of the array after appending.

        Raises:
            RuntimeError: If the RedisJSON module is not available.
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        self._require_json()
        count = await self.client.json().arrappend(key, path, *args)  # type: ignore[no-untyped-call]
        return int(count) if count else 0

    @catch_redis_errors
    async def delete(self, key: str, path: str = "$") -> int:
        """Delete a JSON value at the given path (JSON.DEL).

        Args:
            key: Redis key string.
            path: JSONPath expression. Defaults to ``$`` (the whole document).

        Returns:
            Number of elements deleted.

        Raises:
            RuntimeError: If the RedisJSON module is not available.
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.
        """
        self._require_json()
        result = await self.client.json().delete(key, path)  # type: ignore[no-untyped-call]
        return int(result) if result else 0
