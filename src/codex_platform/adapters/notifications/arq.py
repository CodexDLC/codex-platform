"""
codex_platform.adapters.notifications.arq
========================================
ARQ/Redis adapter for notifications.
"""

import logging
from typing import Any

from codex_platform.adapters.arq.client import BaseArqClient

from .base import NotificationAdapter

log = logging.getLogger(__name__)


class ArqNotificationAdapter(NotificationAdapter):
    """
    Adapter that puts notification tasks into a Redis queue via ARQ.

    Raises on infrastructure failures (Redis unavailable, serialization errors).
    """

    def __init__(self, client: BaseArqClient):
        self.client = client

    def enqueue(self, task_name: str, payload: dict[str, Any]) -> str | None:
        """
        Enqueue a notification task into the ARQ/Redis queue.

        Args:
            task_name: ARQ function name to execute in the worker
                       (e.g. ``'send_universal_notification_task'``).
            payload: Serialized ``NotificationPayloadDTO``.

        Returns:
            Job ID string from ARQ if the job was accepted, None if ARQ
            returned no job handle.

        Raises:
            ConnectionError: Redis is unreachable.
            Exception: Any other ARQ/Redis infrastructure failure.
        """
        log.debug("ArqNotificationAdapter | enqueueing task=%s", task_name)
        result = self.client.enqueue_job(task_name, payload_dict=payload)
        job_id = getattr(result, "job_id", None)
        log.info(
            "ArqNotificationAdapter | task=%s enqueued, job_id=%s",
            task_name,
            job_id,
        )
        return job_id
