"""
codex_platform.notifications.delivery
=======================================
Delivery adapters — the "how" of getting a notification to its destination.

  - ``ArqNotificationAdapter``    → enqueues into Redis/ARQ queue
  - ``DirectNotificationAdapter`` → delivers in-process (sync, no broker)
"""

from .arq import ArqNotificationAdapter
from .base import NotificationAdapter
from .direct import DirectNotificationAdapter

__all__ = [
    "NotificationAdapter",
    "ArqNotificationAdapter",
    "DirectNotificationAdapter",
]
