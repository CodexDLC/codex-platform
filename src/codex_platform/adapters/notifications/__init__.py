"""
codex_platform.adapters.notifications
====================================
Transport adapters for notification delivery.

Adapters handle the *how* of getting a payload to a worker/channel:
  - ArqNotificationAdapter  → puts the job into Redis (ARQ queue)
  - DirectNotificationAdapter → delivers in-process via channel pipeline

For channel implementations (SMTP, DjangoMail, Telegram, etc.),
see ``codex_platform.worker.notifications``.
"""

from .arq import ArqNotificationAdapter
from .base import NotificationAdapter
from .direct import DirectNotificationAdapter

__all__ = [
    "ArqNotificationAdapter",
    "NotificationAdapter",
    "DirectNotificationAdapter",
]
