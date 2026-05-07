"""Deprecated compatibility imports for :mod:`codex_platform.messaging.registry`."""

from __future__ import annotations

import warnings

warnings.warn(
    "codex_platform.notifications.registry is deprecated; use codex_platform.messaging.registry instead.",
    DeprecationWarning,
    stacklevel=2,
)

from codex_platform.messaging.registry import *  # noqa: E402,F401,F403
