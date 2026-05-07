"""Deprecated compatibility imports for :mod:`codex_platform.messaging.delivery.base`."""

from __future__ import annotations

import warnings

warnings.warn(
    "codex_platform.notifications.delivery.base is deprecated; use codex_platform.messaging.delivery.base instead.",
    DeprecationWarning,
    stacklevel=2,
)

from codex_platform.messaging.delivery.base import *  # noqa: E402,F401,F403
