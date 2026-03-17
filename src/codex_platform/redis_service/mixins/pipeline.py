"""
codex_platform.redis_service.mixins.pipeline
==========================================
Redis Pipeline operations mixin.

Requires ``redis.asyncio.Redis`` client (provided by BaseRedisService).
All operations are async-only.

IMPORTANT: builder_func MUST be an async function.
All redis-py async pipeline methods are coroutines.
"""

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from redis.asyncio import Redis
from redis.asyncio.client import Pipeline
from redis.exceptions import RedisError

log = logging.getLogger(__name__)


class PipelineMixin:
    """
    Миксин для работы с пайплайнами (Pipeline) в Redis.

    ВАЖНО: builder_func ДОЛЖНА быть асинхронной функцией.
    Все асинхронные методы пайплайна в redis-py являются корутинами.

    Пример::

        async def build(pipe: Pipeline) -> None:
            await pipe.set("key1", "val1")
            await pipe.set("key2", "val2")

        results = await service.execute_pipeline(build)

    Требует: BaseRedisService (предоставляет self.redis_client)
    """

    redis_client: Redis

    async def execute_pipeline(self, builder_func: Callable[[Pipeline], Awaitable[None]]) -> list[Any]:
        """Выполняет последовательность команд в пайплайне Redis."""
        try:
            async with self.redis_client.pipeline() as pipe:
                await builder_func(pipe)
                results = await pipe.execute()

            log.debug("RedisPipeline | action=execute status=success commands_count=%d", len(results))
            return results

        except RedisError:
            log.exception("RedisPipeline | action=execute status=failed reason='Redis error'")
            return []
        except Exception as e:
            log.exception("RedisPipeline | action=execute status=failed reason='Builder error' error='%s'", e)
            return []
