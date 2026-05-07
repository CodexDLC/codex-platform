"""Deprecated module alias for :mod:`codex_platform.messaging.clients.smtp`."""

from __future__ import annotations

import sys
import warnings

from codex_platform.messaging.clients import smtp as _smtp
from codex_platform.messaging.clients.smtp import _AIOSMTP_AVAILABLE, AsyncEmailClient, aiosmtplib

warnings.warn(
    "codex_platform.notifications.clients.smtp is deprecated; use codex_platform.messaging.clients.smtp instead.",
    DeprecationWarning,
    stacklevel=2,
)

sys.modules[__name__] = _smtp

__all__ = ["AsyncEmailClient", "_AIOSMTP_AVAILABLE", "aiosmtplib"]
