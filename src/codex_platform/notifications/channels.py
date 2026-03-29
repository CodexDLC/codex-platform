"""
codex_platform.notifications.channels
=======================================
Enum of supported notification delivery channels.
"""

from enum import StrEnum


class NotificationChannel(StrEnum):
    """Supported notification delivery channel identifiers."""

    EMAIL = "email"
    TELEGRAM = "telegram"
    SMS = "sms"
    WHATSAPP = "whatsapp"
