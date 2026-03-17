"""
codex_platform.notifications.channels
=======================================
Enum of supported notification delivery channels.
"""

import sys
from enum import Enum

if sys.version_info >= (3, 11):
    from enum import StrEnum
else:
    # Fallback for Python 3.10
    class StrEnum(str, Enum):
        pass


class NotificationChannel(StrEnum):
    """Supported notification delivery channel identifiers."""

    EMAIL = "email"
    TELEGRAM = "telegram"
    SMS = "sms"
    WHATSAPP = "whatsapp"
