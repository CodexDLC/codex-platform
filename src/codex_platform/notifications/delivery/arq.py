"""
codex_platform.notifications.delivery.arq
==========================================
ARQ delivery adapter — enqueues notification tasks into Redis/ARQ queue.

Example::

    from arq.connections import create_pool, RedisSettings
    from codex_platform.notifications.delivery.arq import ArqNotificationAdapter

    pool = await create_pool(RedisSettings())
    adapter = ArqNotificationAdapter(pool)

    # Async context (preferred):
    job_id = await adapter.enqueue_async("send_notification_task", payload)

    # Sync context:
    job_id = adapter.enqueue("send_notification_task", payload)
"""

import logging
from typing import Any

from arq.connections import ArqRedis

from .base import NotificationAdapter

log = logging.getLogger(__name__)


class ArqNotificationAdapter(NotificationAdapter):
    """
    Notification adapter that enqueues tasks into an ARQ/Redis queue.

    Args:
        pool: ``ArqRedis`` connection pool from ``arq.connections.create_pool``.

    Raises on infrastructure failures (Redis unavailable, serialization errors).
    """

    def __init__(self, pool: ArqRedis) -> None:
        self.pool = pool

    def enqueue(self, task_name: str, payload: dict[str, Any]) -> str | None:
        """Sync enqueue — wraps async via asyncio. Use enqueue_async in async contexts."""
        import asyncio
        return asyncio.get_event_loop().run_until_complete(
            self.enqueue_async(task_name, payload)
        )

    async def enqueue_async(self, task_name: str, payload: dict[str, Any]) -> str | None:
        """
        Enqueue a notification task into the ARQ queue (async).

        Args:
            task_name: ARQ worker function name (e.g. ``'send_notification_task'``).
            payload:   Serialized ``NotificationPayloadDTO``.

        Returns:
            Job ID string, or None if ARQ returned no handle.

        Raises:
            ConnectionError: Redis is unreachable.
            Exception: Any ARQ/Redis infrastructure failure.
        """
        log.debug("ArqNotificationAdapter | enqueueing task=%s", task_name)
        job = await self.pool.enqueue_job(task_name, payload_dict=payload)
        job_id = getattr(job, "job_id", None)
        log.info("ArqNotificationAdapter | task=%s job_id=%s", task_name, job_id)
        return job_id
