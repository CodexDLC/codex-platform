"""
codex_platform.redis_service.operations.pipeline
=================================================
Redis Pipeline & Atomic operations.

Two modes:
- ``execute``  — pipeline without MULTI/EXEC (batching, not atomic).
- ``transact`` — pipeline with MULTI/EXEC (atomic transaction).
- ``atomic``   — async context manager that yields a Pipeline in MULTI/EXEC mode.
- ``eval_script`` — Lua script execution (always atomic in Redis).

Usage::

    # Batching (faster, not atomic)
    results = await ops.pipeline.execute(build_fn)

    # Atomic transaction (MULTI/EXEC)
    results = await ops.pipeline.transact(build_fn)

    # Atomic context manager
    async with ops.pipeline.atomic() as pipe:
        await pipe.set("k1", "v1")
        await pipe.incr("counter")
    # committed on exit

    # Lua script
    await ops.pipeline.eval_script(
        "return redis.call('SET', KEYS[1], ARGV[1])",
        keys=["mykey"], args=["value"],
    )
"""

import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any

from redis.asyncio import Redis
from redis.asyncio.client import Pipeline

from codex_platform.redis_service.base import catch_redis_errors
from codex_platform.redis_service.exceptions import RedisConnectionError, RedisServiceError

log = logging.getLogger(__name__)


class PipelineOperations:
    """Redis pipeline and atomic transaction operations.

    Provides three execution modes:

    - **Batching** (``execute``) — commands are sent in one round-trip, not atomic.
    - **Transaction** (``transact``) — commands are wrapped in MULTI/EXEC, atomic.
    - **Context manager** (``atomic``) — atomic block with automatic EXEC on exit.

    Also exposes Lua script execution via ``eval_script``.
    """

    def __init__(self, client: Redis) -> None:
        self.client = client

    @catch_redis_errors
    async def execute(self, builder_func: Callable[[Pipeline], Awaitable[None]]) -> list[Any]:
        """Execute a sequence of commands in a pipeline without MULTI/EXEC (batching).

        Commands are sent in a single round-trip but are **not** atomic.
        Use ``transact`` or ``atomic`` when atomicity is required.

        Args:
            builder_func: Async function that receives a ``Pipeline`` and queues commands.

        Returns:
            List of results for each queued command, in order.

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.

        Example::

            async def build(pipe):
                await pipe.set("k1", "v1")
                await pipe.set("k2", "v2")

            results = await ops.execute(build)
        """
        async with self.client.pipeline(transaction=False) as pipe:
            await builder_func(pipe)
            results = await pipe.execute()
        log.debug("PipelineOps | execute commands=%d", len(results))
        return results

    @catch_redis_errors
    async def transact(self, builder_func: Callable[[Pipeline], Awaitable[None]]) -> list[Any]:
        """Execute commands in an atomic transaction (MULTI/EXEC).

        All commands inside ``builder_func`` are executed atomically.
        If the server crashes before EXEC, none of the commands are applied.

        Args:
            builder_func: Async function that receives a ``Pipeline`` and queues commands.

        Returns:
            List of results for each queued command, in order.

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.

        Example::

            async def transfer(pipe):
                await pipe.decrby("wallet:from", 100)
                await pipe.incrby("wallet:to", 100)

            results = await ops.transact(transfer)
        """
        async with self.client.pipeline(transaction=True) as pipe:
            await builder_func(pipe)
            results = await pipe.execute()
        log.debug("PipelineOps | transact commands=%d", len(results))
        return results

    @asynccontextmanager
    async def atomic(self) -> AsyncIterator[Pipeline]:
        """Async context manager for an atomic block (MULTI/EXEC).

        Opens a Pipeline in transaction mode. EXEC is called automatically on exit.

        Yields:
            ``Pipeline`` instance in MULTI/EXEC mode.

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.

        Example::

            async with service.pipeline.atomic() as pipe:
                await pipe.set("session:abc", "token")
                await pipe.expire("session:abc", 3600)
            # EXEC is called automatically on context exit
        """
        from redis.exceptions import ConnectionError, RedisError, TimeoutError

        pipe: Pipeline = self.client.pipeline(transaction=True)
        try:
            async with pipe as p:
                yield p
                await p.execute()
                log.debug("PipelineOps | atomic block committed")
        except (ConnectionError, TimeoutError) as e:
            raise RedisConnectionError(f"Atomic block connection failed: {e}") from e
        except RedisError as e:
            raise RedisServiceError(f"Atomic block error: {e}") from e

    @catch_redis_errors
    async def eval_script(
        self,
        script: str,
        keys: list[str] | None = None,
        args: list[Any] | None = None,
    ) -> Any:
        """Execute a Lua script (EVAL). Lua scripts are always atomic in Redis.

        Use for complex read-modify-write operations that must not be interrupted.

        Args:
            script: Lua script source code.
            keys: List of Redis keys accessible as ``KEYS[1]``, ``KEYS[2]``, etc.
            args: Script arguments accessible as ``ARGV[1]``, ``ARGV[2]``, etc.

        Returns:
            Value returned by the Lua script.

        Raises:
            RedisConnectionError: Redis connection failure.
            RedisServiceError: Redis operation failure.

        Example::

            result = await ops.eval_script(
                \"\"\"
                local val = redis.call('GET', KEYS[1])
                if val == ARGV[1] then
                    redis.call('SET', KEYS[1], ARGV[2])
                    return 1
                end
                return 0
                \"\"\",
                keys=["mykey"],
                args=["expected", "new_value"],
            )
        """
        result = await self.client.eval(script, len(keys or []), *(keys or []), *(args or []))
        log.debug("PipelineOps | eval_script keys=%d args=%d", len(keys or []), len(args or []))
        return result
