"""Deprecated compatibility imports for :mod:`codex_platform.messaging.interfaces`."""

from __future__ import annotations

import warnings

warnings.warn(
    "codex_platform.notifications.interfaces is deprecated; use codex_platform.messaging.interfaces instead.",
    DeprecationWarning,
    stacklevel=2,
)

from codex_platform.messaging.interfaces import *  # noqa: E402,F401,F403
