"""Protocol definition for notification delivery adapters."""

from __future__ import annotations

from typing import Any, Protocol


class NotificationAdapter(Protocol):
    """Contract for notification delivery transport."""

    def enqueue(self, task_name: str, payload: dict[str, Any]) -> str | None:
        """Deliver or enqueue a serialized notification payload."""
        ...


__all__ = ["NotificationAdapter"]
