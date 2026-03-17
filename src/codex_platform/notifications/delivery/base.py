"""
codex_platform.notifications.delivery.base
==========================================
Protocol definition for notification delivery adapters.
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
            task_name: Worker function name to execute.
                       May be unused by adapters that deliver synchronously.
            payload: Serialized ``NotificationPayloadDTO`` (via ``.model_dump(mode="json")``).

        Returns:
            str: Job/task identifier for tracking.
            None: When the transport is fire-and-forget.

        Raises:
            Exception: Infrastructure errors MUST propagate — never swallow them.
        """
        ...
