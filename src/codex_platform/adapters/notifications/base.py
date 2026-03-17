"""
codex_platform.adapters.notifications.base
=========================================
Protocol definition for notification adapters.
"""

from typing import Any, Protocol


class NotificationAdapter(Protocol):
    """
    Contract for notification delivery transport.

    Allows the same business logic to work with ARQ, Celery, Direct calls,
    or Django's built-in mail system.

    Implementations MUST:
        - Raise exceptions on infrastructure failures (network, broker, DB).
        - Return a job/task ID (str) when the backend provides one.
        - Return None for fire-and-forget transports with no tracking ID.
    """

    def enqueue(self, task_name: str, payload: dict[str, Any]) -> str | None:
        """
        Deliver or enqueue the notification.

        Args:
            task_name: Worker function name to execute (e.g. 'send_universal_notification_task').
                       May be unused by adapters that deliver synchronously — in that case
                       the implementation should accept the argument with a ``_`` prefix.
            payload: Serialized ``NotificationPayloadDTO`` (via ``.model_dump(mode="json")``).

        Returns:
            str: Job/task identifier for tracking (e.g. ARQ job ID).
            None: When the transport is fire-and-forget.

        Raises:
            Exception: Infrastructure errors (Redis down, SMTP failure, DB crash)
                       MUST propagate — adapters must NOT silently swallow them.
        """
        ...
