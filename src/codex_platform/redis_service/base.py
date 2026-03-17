"""
codex_platform.redis_service.base
=================================
Core Redis infrastructure components.

Contains:
- catch_redis_errors — decorator that converts redis-py errors to domain exceptions
- BaseRedisService — base class holding a Redis connection
"""

import logging
from collections.abc import Callable
from functools import wraps
from typing import Any

from redis.asyncio import Redis
from redis.exceptions import ConnectionError, RedisError, TimeoutError

from codex_platform.redis_service.exceptions import RedisConnectionError, RedisServiceError

log = logging.getLogger(__name__)


def catch_redis_errors(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator that converts redis-py exceptions into typed domain exceptions.

    Never suppresses errors — always re-raises as a domain exception.
    Preserves the original traceback via ``raise ... from e``.

    Catches:
        - ``ConnectionError``, ``TimeoutError`` → :exc:`RedisConnectionError`
        - ``RedisError`` → :exc:`RedisServiceError`

    Does NOT catch:
        ``JSONDecodeError``, ``TypeError`` — data-specific errors are caught
        in individual operations and re-raised as :exc:`RedisDataError`.
    """

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await func(*args, **kwargs)
        except (ConnectionError, TimeoutError) as e:
            msg = f"Network failure in {func.__name__}: {e}"
            log.exception("Redis | error=connection_failed fn='%s'", func.__name__)
            raise RedisConnectionError(msg) from e
        except RedisError as e:
            msg = f"Operation failed in {func.__name__}: {e}"
            log.exception("Redis | error=operation_failed fn='%s'", func.__name__)
            raise RedisServiceError(msg) from e

    return wrapper


class BaseRedisService:
    """Base class that holds a Redis connection.

    Inherit from this class when building a service that wraps a Redis client
    but does not need the full :class:`~codex_platform.redis_service.service.RedisService`
    composition.
    """

    def __init__(self, client: Redis) -> None:
        """Initialize the service with an existing async Redis client.

        Args:
            client: An already-constructed ``redis.asyncio.Redis`` instance.
        """
        self.redis_client = client
