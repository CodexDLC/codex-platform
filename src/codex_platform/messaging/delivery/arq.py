"""ARQ delivery adapter for messaging payloads."""

from __future__ import annotations

import logging
from typing import Any

from arq.connections import ArqRedis

from .base import NotificationAdapter

log = logging.getLogger(__name__)


class ArqNotificationAdapter(NotificationAdapter):
    """Notification adapter that enqueues tasks into an ARQ/Redis queue."""

    def __init__(self, pool: ArqRedis) -> None:
        self.pool = pool

    def enqueue(self, task_name: str, payload: dict[str, Any]) -> str | None:
        """Sync enqueue wrapper. Prefer ``enqueue_async`` in async contexts."""

        import asyncio

        return asyncio.get_event_loop().run_until_complete(self.enqueue_async(task_name, payload))

    async def enqueue_async(self, task_name: str, payload: dict[str, Any]) -> str | None:
        """Enqueue a notification task into the ARQ queue."""

        log.debug("ArqNotificationAdapter | enqueueing task=%s", task_name)
        job = await self.pool.enqueue_job(task_name, payload_dict=payload)
        job_id = getattr(job, "job_id", None)
        log.info("ArqNotificationAdapter | task=%s job_id=%s", task_name, job_id)
        return job_id


__all__ = ["ArqNotificationAdapter"]
