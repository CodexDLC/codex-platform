"""
codex_platform.workers.arq.base
============================
Base infrastructure for ARQ background workers.

Usage:
    from codex_platform.workers.arq import BaseArqWorkerSettings, base_startup, base_shutdown

    class MyWorkerSettings(BaseArqWorkerSettings):
        redis_settings = RedisSettings(...)
        functions = MY_FUNCTIONS
        on_startup = my_startup
        on_shutdown = my_shutdown
"""

import logging
import pathlib
from datetime import UTC, datetime
from typing import Any

from arq.connections import ArqRedis, RedisSettings, create_pool

log = logging.getLogger(__name__)


class BaseArqService:
    """Async ARQ client for use inside worker tasks.

    For the Django producer-side client see
    ``codex_platform.adapters.arq.client.BaseArqClient``.

    Example::

        service = BaseArqService(redis_settings)
        await service.init()
        await service.enqueue_job("my_task", arg1, arg2)
        await service.close()
    """

    def __init__(self, redis_settings: RedisSettings) -> None:
        """Initialize the service with Redis connection settings.

        Args:
            redis_settings: ARQ ``RedisSettings`` instance.
        """
        self.pool: ArqRedis | None = None
        self.redis_settings = redis_settings

    async def init(self) -> None:
        """Open the ARQ connection pool. No-op if already initialized.

        Raises:
            Exception: If the Redis connection cannot be established.
        """
        if not self.pool:
            try:
                self.pool = await create_pool(self.redis_settings)
                log.debug("BaseArqService | init | status=success")
            except Exception:
                log.exception("BaseArqService | init | status=failed")
                raise

    async def close(self) -> None:
        """Close the ARQ connection pool gracefully."""
        if self.pool:
            try:
                await self.pool.close()
                log.debug("BaseArqService | close | status=success")
            except Exception:
                log.exception("BaseArqService | close | status=failed")

    async def enqueue_job(self, function: str, *args: Any, **kwargs: Any) -> Any | None:
        """Enqueue a background job. Initializes the pool on first call.

        Args:
            function: ARQ worker function name.
            *args: Positional arguments forwarded to the function.
            **kwargs: Keyword arguments forwarded to the function.

        Returns:
            ARQ ``Job`` handle, or ``None`` if enqueueing failed.
        """
        if not self.pool:
            await self.init()
        if self.pool:
            try:
                job = await self.pool.enqueue_job(function, *args, **kwargs)
                log.debug(
                    "BaseArqService | enqueue_job | function=%s | job_id=%s",
                    function,
                    job.job_id if job else "None",
                )
                return job
            except Exception:
                log.exception("BaseArqService | enqueue_job | function=%s | status=failed", function)
                return None
        return None


# --- Health Check ---
# Marker file for container health probes (Docker HEALTHCHECK, K8s liveness)
HEALTH_FILE = pathlib.Path("/tmp/arq_worker_healthy")  # nosec B108


async def base_startup(ctx: dict[str, Any]) -> None:
    """Base startup hook. Creates health check file. Extend in your workers."""
    HEALTH_FILE.touch()
    log.info("ArqWorker | startup | health_file=%s", HEALTH_FILE)


async def base_shutdown(ctx: dict[str, Any]) -> None:
    """Base shutdown hook. Removes health check file. Extend in your workers."""
    HEALTH_FILE.unlink(missing_ok=True)
    log.info("ArqWorker | shutdown")


class BaseArqWorkerSettings:
    """Base ARQ ``WorkerSettings``. Subclass and override fields in your workers module.

    Example::

        class MyWorkerSettings(BaseArqWorkerSettings):
            redis_settings = RedisSettings(host="localhost", port=6379)
            functions = [my_task1, my_task2] + CORE_FUNCTIONS
            on_startup = my_startup
            on_shutdown = my_shutdown
    """

    max_jobs: int = 20
    job_timeout: int = 60
    keep_result: int = 60
    max_retries: int = 5
    retry_delay: int = 10

    on_startup = base_startup
    on_shutdown = base_shutdown


# --- CORE_FUNCTIONS ---


async def requeue_to_stream(ctx: dict[str, Any], stream_name: str, payload: dict[str, Any]) -> None:
    """Re-enqueue a failed message back into a Redis Stream for retry processing.

    After 5 retries the message is moved to a Dead Letter Queue (DLQ) instead of
    being dropped. DLQ key: ``{stream_name}:dlq``.

    Args:
        ctx:         ARQ worker context dict. Must contain a ``"stream_manager"`` key.
        stream_name: Target Redis Stream name.
        payload:     Original message payload. ``_retries`` counter is incremented in-place.
    """
    sm = ctx.get("stream_manager")
    if not sm:
        log.error("requeue_to_stream | stream_manager not in context")
        return
    retries = int(payload.get("_retries", 0)) + 1
    if retries > 5:
        dlq_name = f"{stream_name}:dlq"
        payload["_failed_at"] = datetime.now(UTC).isoformat()
        payload["_original_stream"] = stream_name
        await sm.add_event(dlq_name, payload)
        log.error("requeue_to_stream | max retries reached | moved to DLQ '%s'", dlq_name)
        return
    payload["_retries"] = str(retries)
    await sm.add_event(stream_name, payload)
    log.info("requeue_to_stream | requeued to '%s' retry=%d", stream_name, retries)


CORE_FUNCTIONS = [requeue_to_stream]
