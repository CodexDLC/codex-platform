"""
codex_platform.adapters.arq.client
=================================
Universal client for ARQ (Producer).

Allows synchronous code to enqueue jobs into an asynchronous Redis queue.
Does not depend directly on Django settings.
"""

import asyncio
from typing import Any

from arq.connections import ArqRedis, RedisSettings, create_pool


class BaseArqClient:
    """
    Base client for interacting with the ARQ queue.
    """

    _pool: ArqRedis | None = None

    def __init__(self, redis_host: str, redis_port: int, redis_password: str | None = None):
        self.redis_settings = RedisSettings(
            host=redis_host,
            port=redis_port,
            password=redis_password,
            database=0,
        )

    async def get_pool(self) -> ArqRedis:
        if self._pool is None:
            self._pool = await create_pool(self.redis_settings)
        return self._pool

    async def enqueue_job_async(self, function: str, *args: Any, **kwargs: Any) -> Any:
        try:
            pool = await self.get_pool()
            return await pool.enqueue_job(function, *args, **kwargs)
        except Exception as e:
            # Better to raise an exception or use a logger in a library
            raise e

    def enqueue_job(self, function: str, *args: Any, **kwargs: Any) -> Any:
        """Synchronous wrapper for use in Django views."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self.enqueue_job_async(function, *args, **kwargs))
